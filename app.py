from utils import (
    system_message, tools, handle_tool_call, talker, artist, openai, MODEL
)
import gradio as gr


########################################
# 7) The Chat Function
########################################
def chat(history, do_tts=True, do_image=False):
    """
    Takes conversation history, returns (new_history, optional_image).
    do_tts: If True, we do talker() for the final text.
    do_image: If True, we generate an image for the destination city if book_flight was called.

    1) We'll parse the entire conversation so far.
    2) We'll see if LLM calls any tool. If tool == 'book_flight', we capture 'destination' for an image.
    3) We'll produce final text. If do_tts=True, we call talker(final_text).
    4) If do_image=True and we have a 'destination' from book_flight, we call artist(destination).
    """
    messages = [{"role": "system", "content": system_message}] + history
    image_to_return = None
    booked_destination = None

    try:
        response = openai.chat.completions.create(model=MODEL, messages=messages, tools=tools)

        # If the LLM calls a tool:
        while response.choices[0].finish_reason == "tool_calls":
            msg = response.choices[0].message
            print(f"[INFO] Tool call requested: {msg.tool_calls[0]}")
            
            tool_response, dest_city = handle_tool_call(msg)
            print(f"[INFO] Tool response: {tool_response}")

            # If it's 'book_flight' or we got a 'dest_city', store it 
            if dest_city:
                booked_destination = dest_city

            messages.append(msg)
            messages.append(tool_response)

            # Re-send updated conversation
            response = openai.chat.completions.create(model=MODEL, messages=messages)

        final_text = response.choices[0].message.content

        # # TTS
        # if do_tts:
        #     talker(final_text)

        # If user wants images and we have a 'book_flight' city:
        if do_image and booked_destination:
            image_to_return = artist(booked_destination)

        new_history = history + [{"role": "assistant", "content": final_text}]

                # TTS
        if do_tts:
            talker(final_text)

        return new_history, image_to_return

    except Exception as e:
        print(f"[ERROR] {e}")
        error_msg = "I'm sorry, something went wrong while processing your request."
        new_history = history + [{"role":"assistant","content":error_msg}]
        return new_history, None

########################################
# 8) Enhanced Gradio UI (Side-by-Side)
########################################
with gr.Blocks() as ui:
    gr.Markdown("## FlightAI Assistant (Flexible Images + TTS)")

    with gr.Row():
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(
                label="FlightAI Chat",
                height=500,
                type="messages",
            )
        with gr.Column(scale=1):
            image_output = gr.Image(
                label="Generated Image (if any)",
                height=500
            )
    
    # Next row: user input + checkboxes for TTS + images
    user_input = gr.Textbox(
        label="Type your message here...",
        placeholder="Ask about flights, destinations, etc.",
    )

    with gr.Row():
        enable_tts_checkbox = gr.Checkbox(label="Enable TTS (Audio)?", value=False)
        enable_image_checkbox = gr.Checkbox(label="Generate Destination Image? ($0.05 each)", value=False)
        clear_btn = gr.Button("Clear Conversation")

    ############################################################################
    # Logic for handling user messages
    ############################################################################
    def user_message(message, chat_history):
        chat_history += [{"role": "user", "content": message}]
        return "", chat_history

    def process_chat(chat_history, do_tts, do_image):
        new_history, maybe_image = chat(chat_history, do_tts=do_tts, do_image=do_image)
        return new_history, maybe_image

    # 1) Submitting the user input
    user_input.submit(
        fn=user_message,
        inputs=[user_input, chatbot],
        outputs=[user_input, chatbot]
    ).then(
        fn=process_chat,
        inputs=[chatbot, enable_tts_checkbox, enable_image_checkbox],
        outputs=[chatbot, image_output]
    )

    # 2) Clear conversation
    def clear_conv():
        return [], None

    clear_btn.click(
        fn=clear_conv,
        outputs=[chatbot, image_output],
        queue=False
    )


# Launch the app
ui.launch()
