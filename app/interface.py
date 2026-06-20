from agents.excutive import ExcutiveAgent
from agents.publisher_agent import PublisherAgent
import asyncio
from typing import Optional

executive_agent = ExcutiveAgent(
    servers=None,
    identity=ExcutiveAgent.identity
)

publisher_agent = PublisherAgent(servers=None, identity=PublisherAgent.identity)

writer_agent = ExcutiveAgent(
    servers=None,
    identity=ExcutiveAgent.identity
)
def is_affirmative(text: str) -> bool:
    """Check if response is affirmative."""
    return text.lower().strip() in ["yes", "y", "ok", "sure", "confirm"]

def is_negative(text: str) -> bool:
    """Check if response is negative."""
    return any([word in text.lower().strip() for word in ["no", "n", "nope", "reject", "cancel"]])

async def main():
    """Main chat loop for CLI interface."""
    current_draft: Optional[str] = None
    
    # Clear any previous history
    executive_agent.clear_history()
    publisher_agent.clear_history()
    writer_agent.clear_history()
    print("=" * 60)
    print("LinkedIn Content Generator - Command Line Chat")
    print("=" * 60)
    print("\nCommands:")
    print("  - Type your content request to generate a LinkedIn post")
    print("  - Reply 'yes' to post the content")
    print("  - Reply 'no' to provide feedback and modify")
    print("  - Type 'quit' or 'exit' to end the session")
    print("\n" + "-" * 60 + "\n")

    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()

            if not user_input:
                print("Bot: Please enter a message.")
                continue

            if user_input.lower() in ["quit", "exit"]:
                print("\nBot: Goodbye!")
                break

            # Handle existing draft
            if current_draft:
                if is_affirmative(user_input):
                    print("\nBot: Preparing the publishing payload and posting on LinkedIn...")
                    publish_prompt = (
                        "The following LinkedIn content has been approved for publishing. "
                        "Use the local tool `post_to_linkedin` to publish it. "
                        "Extract the post text and, if an image URL is present in the content, pass it as `image_url`. "
                        "Do not create new content. Return only the tool result or a concise status message.\n\n"
                        f"Approved content:\n{current_draft}"
                    )
                    publish_response = await publisher_agent.run_prompt(publish_prompt)
                    current_draft = None
                    print(f"Bot: Content posted on LinkedIn. Response: {publish_response}")
                    continue

                if is_negative(user_input):
                    print("\nBot: Okay, I will update the draft using your feedback.")
                    modified_draft = await writer_agent.run_prompt(
                        f"Please modify the content as per the following feedback: {user_input}. Original content: {current_draft}, and generate an updated version of the LinkedIn post. Return only the modified content without any explanations."
                    )

                    if modified_draft:
                        current_draft = modified_draft
                        print(f"\nBot: Modified content:\n\n{modified_draft}\n")
                        print("Bot: Please review and reply with 'yes' to post or 'no' to provide more feedback.")
                    else:
                        print("Bot: I could not update the draft. Please share your feedback again.")
                    continue

                # Unknown response while draft exists
                print("\nBot: I already have a draft for you. Reply with 'yes' to post it or 'no' to provide feedback.")
                continue

            # Generate new draft from user input
            print("\nBot: Generating LinkedIn content...")
            generated_draft = await executive_agent.run_prompt(user_input)

            if not generated_draft:
                print("Bot: I could not generate LinkedIn content from your request. Please try again.")
                continue

            current_draft = generated_draft
            print(f"\nBot: Generated LinkedIn post:\n\n{generated_draft}\n")
            print("Bot: Please review and reply with 'yes' to post it or 'no' to make changes.")

        except KeyboardInterrupt:
            print("\n\nBot: Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"Bot: Error occurred: {e}")
            print("Bot: Please try again.")

if __name__ == "__main__":
    asyncio.run(main())