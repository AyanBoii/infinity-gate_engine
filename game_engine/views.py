from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
import sys
import os
import json

# Import the GeminiRPG class from main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import GeminiRPG

# Initialize the GeminiRPG instance
rpg_game = GeminiRPG()
rpg_game.setup_api()

def index(request):
    # Reset any previous game state
    if 'story_context' in request.session:
        request.session.pop('story_context')
    if 'character_name' in request.session:
        request.session.pop('character_name')
    
    return render(request, 'index.html')

@csrf_exempt
def world(request):
    if request.method == 'POST':
        # User clicked "Begin Your Adventure" on the index page
        return render(request, 'world.html', {'genres': rpg_game.genres})
    else:
        # Direct access to /world/ URL
        return render(request, 'world.html', {'genres': rpg_game.genres})

@csrf_exempt
def character(request):
    if request.method == 'POST':
        # Store world settings in session from world.html form
        request.session['genre'] = request.POST.get('genre')
        request.session['world_description'] = request.POST.get('world_description')
        request.session['main_conflict'] = request.POST.get('main_conflict')
        
        # Set up story settings in the RPG game instance
        rpg_game.story_settings = {
            'genre': request.session['genre'],
            'world_description': request.session['world_description'],
            'main_conflict': request.session['main_conflict']
        }
        
        # Show character creation page
        backgrounds = [
            "Warrior", "Mage", "Rogue", "Diplomat", "Scholar", "Merchant"
        ]
        return render(request, 'character.html', {'backgrounds': backgrounds})
    else:
        # Direct access to /character/ URL without completing world form
        return redirect('world')

@csrf_exempt
def game(request):
    story = None
    
    if request.method == 'POST':
        # Check if this is coming from character creation form
        if 'name' in request.POST:
            # Store character information in session
            request.session['character_name'] = request.POST.get('name')
            request.session['background'] = request.POST.get('background')
            request.session['traits'] = request.POST.get('traits')
            request.session['description'] = request.POST.get('description')
            
            # Set up character in the RPG game instance
            rpg_game.character = {
                'name': request.session['character_name'],
                'background': request.session['background'],
                'traits': request.session['traits'],
                'description': request.session['description']
            }
            
            # Generate initial story context using Gemini API
            try:
                # Build a story prompt based on world and character
                prompt = f"""
                You are a game master for an interactive text adventure game.
                
                WORLD SETTING:
                Genre: {request.session.get('genre')}
                Description: {request.session.get('world_description')}
                Main Conflict: {request.session.get('main_conflict')}
                
                CHARACTER:
                Name: {request.session.get('character_name')}
                Background: {request.session.get('background')}
                Traits: {request.session.get('traits')}
                Description: {request.session.get('description')}
                
                Begin an epic adventure for this character in this world. Set the scene and end with a situation that requires the player to make a choice.
                Write this in second person perspective (using "you").
                Keep it under 250 words.
                """
                
                response = rpg_game.model.generate_content(prompt)
                story = response.text
                request.session['story_context'] = story
                request.session['story_history'] = [story]
                
            except Exception as e:
                story = f"<p>Error generating story: {str(e)}</p>"
                story += "<p>You find yourself in a mysterious world. What would you like to do?</p>"
        
        # Check if this is a player action during the game
        elif 'choice' in request.POST:
            player_choice = request.POST.get('choice')
            
            try:
                # Get previous story context
                story_context = request.session.get('story_context', '')
                story_history = request.session.get('story_history', [])
                
                # Generate response to player's choice
                prompt = f"""
                You are a game master for an interactive text adventure game.
                
                WORLD SETTING:
                Genre: {request.session.get('genre')}
                Description: {request.session.get('world_description')}
                Main Conflict: {request.session.get('main_conflict')}
                
                CHARACTER:
                Name: {request.session.get('character_name')}
                Background: {request.session.get('background')}
                Traits: {request.session.get('traits')}
                
                STORY SO FAR:
                {story_context}
                
                PLAYER'S ACTION:
                {player_choice}
                
                Continue the story based on the player's action. Be creative and responsive to what they want to do.
                End with a new situation that requires the player to make another choice.
                Write this in second person perspective (using "you").
                Keep it under 250 words.
                """
                
                response = rpg_game.model.generate_content(prompt)
                new_story = response.text
                
                # Update story context and history
                request.session['story_context'] = story_context + "\n\nPlayer: " + player_choice + "\n\n" + new_story
                story_history.append("Player: " + player_choice)
                story_history.append(new_story)
                request.session['story_history'] = story_history
                
                story = new_story
                
            except Exception as e:
                story = f"<p>Error processing your action: {str(e)}</p>"
                story += "<p>What would you like to do next?</p>"
    else:
        # Check if there's an existing story in the session
        if 'story_context' in request.session:
            story = request.session.get('story_history', [])[-1]
        else:
            # Direct access to /game/ URL without completing character form
            return redirect('world')
    
    return render(request, 'game.html', {'story': story}) 