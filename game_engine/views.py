from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import sys
import os
import json
import uuid
import re
import traceback
from django.conf import settings
from .models import GameSession

# Import the Google Generative AI library
import google.generativeai as genai

# Initialize Gemini API
API_KEY = os.environ.get('GEMINI_API_KEY', '')
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

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
        return render(request, 'world.html', {'genres': ["Fantasy", "Sci-Fi", "Cyberpunk", "Post-Apocalyptic", "Steampunk", "Modern", "Horror"]})
    else:
        # Direct access to /world/ URL
        return render(request, 'world.html', {'genres': ["Fantasy", "Sci-Fi", "Cyberpunk", "Post-Apocalyptic", "Steampunk", "Modern", "Horror"]})

@csrf_exempt
def character(request):
    if request.method == 'POST':
        # Store world settings in session from world.html form
        request.session['genre'] = request.POST.get('genre')
        request.session['world_description'] = request.POST.get('world_description')
        request.session['main_conflict'] = request.POST.get('main_conflict')
        
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
                
                response = model.generate_content(prompt)
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
                
                response = model.generate_content(prompt)
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

# API endpoint functions for the React frontend
@csrf_exempt
def create_game_session(request):
    """Create a new game session and return the session ID"""
    if request.method == 'POST':
        try:
            # Parse JSON data from request
            data = json.loads(request.body)
            
            # Create a unique session ID
            session_id = str(uuid.uuid4())
            
            print(f"Creating new session with ID: {session_id}")
            
            # Create game state
            game_state = {
                'character': {
                    'name': data.get('character_name', 'Adventurer'),
                    'background': data.get('background', ''),
                    'traits': data.get('traits', ''),
                    'description': data.get('description', '')
                },
                'world': {
                    'genre': data.get('genre', 'Fantasy'),
                    'description': data.get('world_description', ''),
                    'main_conflict': data.get('main_conflict', '')
                },
                'story_history': []
            }
            
            # Generate initial scene for the game
            initial_scene = _generate_initial_scene(request, session_id, game_state)
            
            # Store the initial scene in game state
            game_state['current_scene'] = initial_scene
            
            # Save to database
            GameSession.objects.create(
                session_id=uuid.UUID(session_id),
                game_state=game_state
            )
            
            print(f"Game session saved to database with ID: {session_id}")
            
            # Return the session ID and initial scene
            return JsonResponse({
                'session_id': session_id,
                'scene_text': initial_scene.get('scene_text', ''),
                'options': initial_scene.get('options', []),
                'image_url': initial_scene.get('image_url', None)
            })
            
        except Exception as e:
            print(f"Error creating session: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

def get_game_scene(request, session_id):
    """Get the current scene for a game session"""
    try:
        print(f"Retrieving scene for session ID: {session_id}")
        
        # Get game state from database
        try:
            game_session = GameSession.objects.get(session_id=session_id)
            game_state = game_session.game_state
            print(f"Game state found in database")
        except GameSession.DoesNotExist:
            print(f"Session not found: {session_id}")
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        # Get current scene
        current_scene = game_state.get('current_scene', {})
        
        # If no current scene, generate one
        if not current_scene:
            print(f"No current scene found, generating initial scene for {session_id}")
            current_scene = _generate_initial_scene(request, session_id, game_state)
            # Update the game state with the new scene
            game_state['current_scene'] = current_scene
            game_session.game_state = game_state
            game_session.save()
        
        print(f"Returning scene with text: {current_scene.get('scene_text', '')[:50]}...")
        
        return JsonResponse(current_scene)
            
    except Exception as e:
        print(f"Error getting scene: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def make_choice(request, session_id):
    """Handle a player's choice and update the game state"""
    if request.method == 'POST':
        try:
            # Parse JSON data from request
            data = json.loads(request.body)
            choice_index = data.get('choice_index')
            
            print(f"Processing choice {choice_index} for session {session_id}")
            
            # Get game state from database
            try:
                game_session = GameSession.objects.get(session_id=session_id)
                game_state = game_session.game_state
                print(f"Game state found in database")
            except GameSession.DoesNotExist:
                print(f"Session not found: {session_id}")
                return JsonResponse({'error': 'Session not found'}, status=404)
            
            # Get current scene
            current_scene = game_state.get('current_scene', {})
            if not current_scene:
                return JsonResponse({'error': 'No current scene found'}, status=400)
            
            # Get options
            options = current_scene.get('options', [])
            if not options or choice_index >= len(options):
                return JsonResponse({'error': 'Invalid choice index'}, status=400)
            
            # Get selected option
            selected_option = options[choice_index]
            
            # Add current scene and choice to history
            history_entry = {
                'scene_text': current_scene.get('scene_text', ''),
                'choice': selected_option
            }
            game_state['story_history'].append(history_entry)
            
            # Generate new scene based on the choice
            new_scene = _generate_scene_for_choice(request, session_id, game_state, selected_option)
            
            # Update game state
            game_state['current_scene'] = new_scene
            game_session.game_state = game_state
            game_session.save()
            
            print(f"New scene generated and saved")
            
            # Return the new scene
            return JsonResponse({
                'scene_text': new_scene.get('scene_text', ''),
                'options': new_scene.get('options', []),
                'image_url': new_scene.get('image_url', None)
            })
            
        except Exception as e:
            print(f"Error processing choice: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

def _generate_initial_scene(request, session_id, game_state):
    """Generate the initial scene for a new game"""
    try:
        print(f"Generating initial scene for session {session_id}")
        
        # Get character and world info
        character = game_state.get('character', {})
        world = game_state.get('world', {})
        
        # Create a prompt for Gemini
        character_name = character.get('name', 'Adventurer')
        character_background = character.get('background', '')
        character_traits = character.get('traits', '')
        character_description = character.get('description', '')
        
        world_genre = world.get('genre', 'Fantasy')
        world_description = world.get('description', '')
        world_conflict = world.get('main_conflict', '')
        
        prompt = f"""
        You are starting a text-based role-playing game. Generate the opening scene based on the following:
        
        Character: {character_name}
        Background: {character_background}
        Traits: {character_traits}
        Description: {character_description}
        
        World Genre: {world_genre}
        World Description: {world_description}
        Main Conflict: {world_conflict}
        
        Create an opening scene with 3 possible choices for the player to make.
        Return your response in this JSON format:
        {{
            "scene_text": "Detailed description of the opening scene",
            "options": [
                "First choice for the player",
                "Second choice for the player",
                "Third choice for the player"
            ]
        }}
        """
        
        # Use Gemini to generate the scene
        response = model.generate_content(prompt)
        
        # Parse the response
        try:
            # Try to extract JSON from the response
            content = response.text
            json_match = re.search(r'{.*}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            scene_data = json.loads(content)
            print(f"Scene generated successfully")
            return scene_data
        except Exception as e:
            print(f"Error parsing scene data: {str(e)}")
            print(f"Raw response: {response.text}")
            # Fallback to a simple scene
            return {
                "scene_text": f"You find yourself in a mysterious world. Welcome, {character_name}, to your adventure.",
                "options": [
                    "Explore the immediate surroundings",
                    "Look for other people",
                    "Check your belongings"
                ]
            }
    except Exception as e:
        print(f"Error generating initial scene: {str(e)}")
        print(traceback.format_exc())
        # Return a fallback scene
        return {
            "scene_text": "You wake up in a strange place, unsure of how you got here.",
            "options": [
                "Look around",
                "Call out for help",
                "Try to remember what happened"
            ]
        }

def _generate_scene_for_choice(request, session_id, game_state, selected_option):
    """Generate a new scene based on the player's choice"""
    try:
        print(f"Generating new scene for session {session_id} based on choice: {selected_option}")
        
        # Get character info and story history
        character = game_state.get('character', {})
        character_name = character.get('name', 'Adventurer')
        story_history = game_state.get('story_history', [])
        
        # Create a context summary from history
        context = ""
        for entry in story_history[-3:]:  # Use the last 3 entries for context
            scene = entry.get('scene_text', '')
            choice = entry.get('choice', '')
            context += f"Scene: {scene}\nPlayer chose: {choice}\n\n"
        
        # Create prompt for Gemini
        prompt = f"""
        You are continuing a text-based role-playing game. Generate the next scene based on the player's choice.
        
        Character name: {character_name}
        
        Recent history:
        {context}
        
        Player's choice: {selected_option}
        
        Create the next scene with 3 possible choices for the player to make.
        Return your response in this JSON format:
        {{
            "scene_text": "Detailed description of the next scene based on the player's choice",
            "options": [
                "First choice for the player",
                "Second choice for the player",
                "Third choice for the player"
            ]
        }}
        """
        
        # Use Gemini to generate the scene
        response = model.generate_content(prompt)
        
        # Parse the response
        try:
            # Try to extract JSON from the response
            content = response.text
            json_match = re.search(r'{.*}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            scene_data = json.loads(content)
            print(f"New scene generated successfully")
            return scene_data
        except Exception as e:
            print(f"Error parsing scene data: {str(e)}")
            print(f"Raw response: {response.text}")
            # Fallback to a simple scene
            return {
                "scene_text": f"You continue your journey. The world responds to your choice.",
                "options": [
                    "Continue forward",
                    "Take a different path",
                    "Rest for a while"
                ]
            }
    except Exception as e:
        print(f"Error generating scene for choice: {str(e)}")
        print(traceback.format_exc())
        # Return a fallback scene
        return {
            "scene_text": "Your journey continues. What will you do next?",
            "options": [
                "Proceed cautiously",
                "Be bold and assertive",
                "Look for an alternative approach"
            ]
        }

def debug_session(request):
    """Debug view to check session state"""
    session_data = {
        'session_key': request.session.session_key,
        'is_empty': len(request.session.keys()) == 0,
        'keys': list(request.session.keys()),
        'modified': request.session.modified,
    }
    
    return JsonResponse(session_data) 