from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def world(request):
    genres = [
        "Fantasy", "Sci-Fi", "Historical", "Post-Apocalyptic", 
        "Cyberpunk", "Steampunk", "Horror", "Mystery"
    ]
    
    if request.method == 'POST':
        return redirect('character')
        
    return render(request, 'world.html', {'genres': genres})
    
@csrf_exempt
def character(request):
    backgrounds = [
        "Warrior", "Mage", "Rogue", "Diplomat", "Scholar", "Merchant"
    ]
    
    if request.method == 'POST':
        # Store world settings in session
        request.session['genre'] = request.POST.get('genre')
        request.session['world_description'] = request.POST.get('world_description')
        request.session['main_conflict'] = request.POST.get('main_conflict')
        return redirect('game')
        
    return render(request, 'character.html', {'backgrounds': backgrounds})
    
@csrf_exempt
def game(request):
    story = None
    
    if request.method == 'POST':
        # Store character information in session
        request.session['character_name'] = request.POST.get('name', request.session.get('character_name'))
        request.session['background'] = request.POST.get('background', request.session.get('background'))
        request.session['traits'] = request.POST.get('traits', request.session.get('traits'))
        request.session['description'] = request.POST.get('description', request.session.get('description'))
        
        # Get player's choice
        choice = request.POST.get('choice')
        
        # Here you would typically process the game state and return a new story segment
        # For now, we'll just display some text based on the character
        if 'character_name' in request.session:
            character_name = request.session.get('character_name')
            background = request.session.get('background')
            story = f"<p>Welcome, {character_name} the {background}!</p>"
            story += "<p>Your adventure is just beginning. What would you like to do?</p>"
    
    return render(request, 'game.html', {'story': story}) 