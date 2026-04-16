import re
import os
from typing import Any, Text, Dict, List
from datetime import datetime
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
######### Conversation Logger #########
#  Logging Utility
LOG_BASE_DIR = "log"

def get_log_filepath() -> str:
    """ 
    Returns the log file path based on current month.
    Structure: log/log_March.txt
    A new file is created automatically each new month.
    """
    month_name = datetime.now().strftime("%B")  # e.g. "March"
    os.makedirs(LOG_BASE_DIR, exist_ok=True)
    return os.path.join(LOG_BASE_DIR, f"log_{month_name}.txt")


def log_action(bot_response: str, tracker: Tracker) -> None:
    """
    Appends a User turn followed by a Bot turn to the daily log file.

    Format:
    2026-03-04 14:32:10.123456	user_abc123  User:  hello  [greet]  [0.97]
    2026-03-04 14:32:10.234567	user_abc123  Bot:   Good Afternoon! I'm AVA...
    """
    filepath   = get_log_filepath()
    now        = datetime.now()
    sender_id  = tracker.sender_id

    user_msg   = tracker.latest_message.get("text", "")
    intent     = tracker.latest_message.get("intent", {}).get("name", "")
    confidence = tracker.latest_message.get("intent", {}).get("confidence", 0.0)

    user_ts = str(now)
    bot_ts  = str(datetime.now())

    user_line = f"{user_ts}\t{sender_id}  User:  {user_msg}  [{intent}]  [{confidence}]\n"
    bot_line  = f"{bot_ts}\t{sender_id}  Bot:  {bot_response}\n\n"

    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(user_line)
            f.write(bot_line)
    except Exception as e:
        print(f"[Logger] Failed to write log: {e}")


####### Greeting Action #######
class ActionGreet(Action):
    
    def name(self) -> Text:
        return "action_greet"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            greeting = "Good morning!"
        elif 12 <= current_hour < 18:
            greeting = "Good afternoon!"
        else:
            greeting = "Good evening!"
        
        message = f"{greeting} How can I assist you today?"

        dispatcher.utter_message(text=message)
        log_action(message, tracker)

        return []
    

















########## Fallback Action ##########
#This action is connected with a LLM Service
class ActionDefaultFallback(Action):

    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text")

        try:
            # 🔥 API Call
            response = requests.post(
                "http://127.0.0.1:5030/",
                json={"question": user_message},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # Adjust key based on your API response
                answer = data.get("answer") or data.get("response") or str(data)

                dispatcher.utter_message(text=answer)
                log_action(answer, tracker)

            else:
                fallback_msg = "I'm having trouble getting an answer right now. Please try again."
                dispatcher.utter_message(text=fallback_msg)
                log_action(fallback_msg, tracker)

        except requests.exceptions.Timeout:
            timeout_msg = "Request timed out. Please try again later."
            dispatcher.utter_message(text=timeout_msg)
            log_action(timeout_msg, tracker)

        except Exception as e:
            error_msg = "Sorry, something went wrong while processing your request."
            dispatcher.utter_message(text=error_msg)
            print(f"[Fallback Error]: {e}")
            log_action(error_msg, tracker)

        return []
