# Gemini RPG - The Multiverse Chronicles

## Overview

Gemini RPG is an AI-powered text adventure game that allows players to explore a multiverse of branching storylines where their choices shape the narrative. The game utilizes Google's Gemini API to generate dynamic story content based on user input.

## Features

- Interactive text-based gameplay
- Customizable character creation
- Dynamic world settings
- AI-generated storylines based on player choices
- Admin interface for managing users and game settings

## Technologies Used

- Django (4.2.7)
- PostgreSQL for database management
- Google Gemini API for AI-generated content
- HTML/CSS for frontend design
- Python (3.10.16)

## Installation

1. Clone the repository:

   ```bash
   https://github.com/AyanBoii/infinity-gate_engine.git
   cd infinity-gate_engine.git
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   # source venv/bin/activate  # On macOS/Linux
   ```

3. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```
   Then run the following:
   1. `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`
   2. `pip install diffusers transformers accelerate safetensors`
   3. `pip install huggingface_hub[hf_xet]`
   4. `pip install peft`

4. Set up PostgreSQL:
   - Create a database named `codehive`.
   - Update the `.env` file with your PostgreSQL credentials.
	  Creating `codehive`:
		- run `psql --version` to verify installation
		- check if PostgreSQL is accepting connections
		- run: ```psql -U postgres -c "CREATE DATABASE codehive;" -c "CREATE USER postgres WITH PASSWORD '<your psql password>';" -c "ALTER USER postgres WITH SUPERUSER;"``` to create the codehive DB
		- run: ```psql -U postgres -d codehive -c "\l"``` to verify if everything is working correctly.

5. Run migrations:

   ```bash
   python manage.py migrate
   ```

6. Create a superuser to access the admin interface:

   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:

   ```bash
   python manage.py runserver
   ```

8. Access the application at `http://127.0.0.1:8000/`.

## Usage

- Begin your adventure by clicking "Begin Your Adventure" on the main page.
- Follow the prompts to set up the world and create your character.
- Interact with the game as the AI generates story content based on your choices.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or features you'd like to add.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google Gemini API for providing AI-generated content.
- Django for the web framework.
- PostgreSQL for database management.