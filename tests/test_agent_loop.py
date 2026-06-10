import json

from app.application.agent_loop import agent_loop
from app.domain.models import Message, ModelReply, Role
from tests.conftest import ScriptedChatModel, market_tools, reply_with_text, reply_with_tool_call


def initial_messages() -> list[Message]:
    return [
        Message(role=Role.SYSTEM, content="system prompt"),
        Message(role=Role.USER, content="precio de apple?"),
    ]


async def test_direct_answer_without_tools():
    model = ScriptedChatModel([reply_with_text("Hola, soy tu asistente financiero.")])

    result = await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=5
    )

    assert result.content == "Hola, soy tu asistente financiero."
    assert result.iterations == 1
    assert result.steps == ()
    assert len(model.calls) == 1
    assert len(model.calls[0]["tools"]) == 4


async def test_tool_call_then_answer():
    model = ScriptedChatModel(
        [
            reply_with_tool_call("get_stock_quote", {"symbol": "AAPL"}),
            reply_with_text("AAPL cotiza a 290.5 USD."),
        ]
    )

    result = await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=5
    )

    assert result.content == "AAPL cotiza a 290.5 USD."
    assert result.iterations == 2
    assert [step.tool_name for step in result.steps] == ["get_stock_quote"]

    second_call_messages = model.calls[1]["messages"]
    tool_message = second_call_messages[-1]
    assert tool_message.role is Role.TOOL
    assert tool_message.tool_call_id == "call_1"
    assert json.loads(tool_message.content)["price"] == 290.5


async def test_unknown_tool_is_reported_back_to_the_model():
    model = ScriptedChatModel(
        [
            reply_with_tool_call("get_crypto_forecast", {"symbol": "BTC"}),
            reply_with_text("No tengo esa herramienta disponible."),
        ]
    )

    result = await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=5
    )

    tool_message = model.calls[1]["messages"][-1]
    assert "Unknown tool" in tool_message.content
    assert result.iterations == 2


async def test_tool_error_is_returned_as_data_not_exception():
    model = ScriptedChatModel(
        [
            reply_with_tool_call("get_stock_quote", {"symbol": "FAIL"}),
            reply_with_text("No encontré datos para ese símbolo."),
        ]
    )

    result = await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=5
    )

    tool_message = model.calls[1]["messages"][-1]
    assert json.loads(tool_message.content)["error"] == "No quote found for 'FAIL'"
    assert result.content == "No encontré datos para ese símbolo."


async def test_invalid_tool_arguments_are_reported_back_to_the_model():
    model = ScriptedChatModel(
        [
            reply_with_tool_call("get_stock_quote", {"ticker": "AAPL"}),
            reply_with_text("Hubo un problema con los argumentos."),
        ]
    )

    await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=5
    )

    tool_message = model.calls[1]["messages"][-1]
    assert "Invalid arguments" in tool_message.content


async def test_max_iterations_forces_a_final_answer_without_tools():
    model = ScriptedChatModel(
        [
            reply_with_tool_call("get_stock_quote", {"symbol": "AAPL"}, call_id="call_1"),
            reply_with_tool_call("get_stock_quote", {"symbol": "MSFT"}, call_id="call_2"),
            reply_with_text("Resumen con lo que pude obtener."),
        ]
    )

    result = await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=2
    )

    assert result.content == "Resumen con lo que pude obtener."
    assert result.iterations == 3
    assert model.calls[-1]["allow_tool_use"] is False
    assert len(model.calls[-1]["tools"]) == 4


async def test_usage_is_accumulated_across_iterations():
    model = ScriptedChatModel(
        [
            reply_with_tool_call("get_stock_quote", {"symbol": "AAPL"}, input_tokens=100),
            reply_with_text("Listo.", input_tokens=200, output_tokens=20),
        ]
    )

    result = await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=5
    )

    assert result.usage.input_tokens == 300
    assert result.usage.output_tokens == 25
    assert result.usage.total_tokens == 325


async def test_multiple_tool_calls_in_one_iteration():
    model = ScriptedChatModel(
        [
            ModelReply(
                content="",
                tool_calls=(
                    reply_with_tool_call("get_stock_quote", {"symbol": "AAPL"}).tool_calls[0],
                    reply_with_tool_call(
                        "get_company_profile", {"symbol": "AAPL"}, call_id="call_2"
                    ).tool_calls[0],
                ),
            ),
            reply_with_text("Apple cotiza a 290.5 USD y pertenece al sector tecnológico."),
        ]
    )

    result = await agent_loop(
        chat_model=model, messages=initial_messages(), tools=market_tools(), max_iterations=5
    )

    assert [step.tool_name for step in result.steps] == ["get_stock_quote", "get_company_profile"]
    tool_messages = [m for m in model.calls[1]["messages"] if m.role is Role.TOOL]
    assert {m.tool_call_id for m in tool_messages} == {"call_1", "call_2"}
