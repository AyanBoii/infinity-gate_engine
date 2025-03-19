import os
import time
import json
import random
from IPython.display import clear_output
import getpass

import google.generativeai as genai

class GeminiRPG:
    def __init__(self):
        self.api_key = None
        self.model = None
        self.genres = ["Fantasy", "Sci-Fi", "Historical", "Post-Apocalyptic", "Cyberpunk", "Steampunk", "Horror", "Mystery"]
        self.character = {}
        self.story_settings = {}
        self.story_context = ""
        self.story_history = []
        
    def setup_api(self):
        print("🔑 Google Gemini API Setup")
        print("--------------------------")
        self.api_key = "AIzaSyCp_NwwtbGzk-PBxtIsREPhwm0xAJZ8CGk"  # Replace with your actual API key
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            print("✅ API connection successful!")
            return True
        except Exception as e:
            print(f"❌ Error setting up API: {e}")
            return False
            
    def welcome_screen(self):
        clear_output(wait=True)
        print("""
        ╔══════════════════════════════════════════════════════╗
        ║                                                      ║
        ║    🌟 GEMINI RPG - THE MULTIVERSE CHRONICLES 🌟     ║
        ║                                                      ║
        ╚══════════════════════════════════════════════════════╝
        
        An AI-powered text adventure with branching storylines where YOUR choices shape the narrative.
        Explore multiple genres and create your unique adventure!
        
        """)
        time.sleep(2)
    
    def customize_character(self):
        clear_output(wait=True)
        print("🧙 CHARACTER CREATION 🧙")
        print("------------------------")
        
        self.character["name"] = input("What is your character's name? > ")
        
        print("\nChoose your character's background:")
        backgrounds = ["Noble", "Commoner", "Outcast", "Scholar", "Warrior", "Mystic"]
        for i, bg in enumerate(backgrounds, 1):
            print(f"{i}. {bg}")
        choice = int(input("Enter your choice (1-6): "))
        self.character["background"] = backgrounds[choice-1]
        
        print("\nChoose three character traits (separate with commas):")
        traits = input("e.g., brave, curious, stubborn > ")
        self.character["traits"] = [trait.strip() for trait in traits.split(",")]
        
        print("\nDescribe your character in a few sentences:")
        self.character["description"] = input("> ")
        
        print("\n✅ Character created successfully!")
        time.sleep(1)
    
    def choose_setting(self):
        clear_output(wait=True)
        print("🌍 WORLD SETTING 🌍")
        print("-------------------")
        
        print("Choose a genre for your adventure:")
        for i, genre in enumerate(self.genres, 1):
            print(f"{i}. {genre}")
        choice = int(input("Enter your choice (1-8): "))
        self.story_settings["genre"] = self.genres[choice-1]
        
        print(f"\nDescribe the world of your {self.story_settings['genre']} adventure:")
        self.story_settings["world_description"] = input("> ")
        
        print("\nWhat is the main conflict or quest in this world?")
        self.story_settings["main_conflict"] = input("> ")
        
        print("\n✅ World setting configured!")
        time.sleep(1)
    
    def generate_story_context(self):
        self.story_context = f"""
        You are the Game Master for an immersive text-based RPG adventure.
        
        GENRE: {self.story_settings['genre']}
        
        WORLD: {self.story_settings['world_description']}
        
        MAIN CONFLICT: {self.story_settings['main_conflict']}
        
        CHARACTER:
        - Name: {self.character['name']}
        - Background: {self.character['background']}
        - Traits: {', '.join(self.character['traits'])}
        - Description: {self.character['description']}
        
        GUIDELINES:
        1. Create a rich, immersive narrative with vivid descriptions.
        2. Offer meaningful choices (3 options) at the end of each passage that impact the story.
        3. Remember player's previous choices and incorporate consequences.
        4. Include occasional challenges/battles with simple mechanics.
        5. Introduce interesting NPCs with distinct personalities.
        6. Create branching storylines where choices truly matter.
        7. Include occasional twists and surprises to keep the narrative engaging.
        8. Maintain the established tone of the chosen genre.
        9. Keep responses focused on advancing the story.
        10. Do not summarize or explain the story structure. Stay in character as the Game Master.
        
        Begin the adventure with an engaging introduction to the world and the character's situation.
        """
        
    def get_ai_response(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return "The Game Master seems to be taking a break. Let's try again."
    
    def start_game(self):
        clear_output(wait=True)
        print("🎮 Preparing your adventure...")
        self.generate_story_context()
        
        # Generate the initial story segment
        initial_prompt = self.story_context + "\nBegin the adventure with an engaging introduction."
        story_response = self.get_ai_response(initial_prompt)
        self.story_history.append({"role": "system", "content": story_response})
        
        self.game_loop()
    
    def game_loop(self):
        game_active = True
        
        while game_active:
            clear_output(wait=True)
            
            # Display the latest story segment
            print("\n" + self.story_history[-1]["content"] + "\n")
            
            # Get player choice
            player_choice = input("What will you do? (or type 'quit' to exit) > ")
            
            if player_choice.lower() == 'quit':
                game_active = False
                print("\nThanks for playing!")
                break
            
            # Construct prompt with history context
            prompt = self.story_context + "\n\nSTORY SO FAR:\n"
            for entry in self.story_history[-3:]:  # Include only recent history to stay within token limits
                prompt += entry["content"] + "\n\n"
            
            prompt += f"PLAYER CHOICE: {player_choice}\n\nContinue the story based on this choice. Remember to end with 2-3 meaningful options for the player's next action."
            
            # Get AI response
            story_response = self.get_ai_response(prompt)
            self.story_history.append({"role": "user", "content": player_choice})
            self.story_history.append({"role": "system", "content": story_response})
    
    def save_game(self):
        save_data = {
            "character": self.character,
            "story_settings": self.story_settings,
            "story_history": self.story_history
        }
        
        with open(f"gemini_rpg_save_{int(time.time())}.json", "w") as f:
            json.dump(save_data, f)
        
        print("Game saved successfully!")
    
    def load_game(self, filename):
        try:
            with open(filename, "r") as f:
                save_data = json.load(f)
                
            self.character = save_data["character"]
            self.story_settings = save_data["story_settings"]
            self.story_history = save_data["story_history"]
            self.generate_story_context()
            
            print("Game loaded successfully!")
            time.sleep(1)
            self.game_loop()
            
        except Exception as e:
            print(f"Error loading game: {e}")

# Run the game
if __name__ == "__main__" or "__file__" not in globals():
    game = GeminiRPG()
    if game.setup_api():
        game.welcome_screen()
        game.customize_character()
        game.choose_setting()
        game.start_game()