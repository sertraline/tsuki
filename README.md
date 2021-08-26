## TSUKI source code
## Setup
Get your bot API token from BotFather and also get a virustotal API key.  
Copy `.env.example` to `.env` and put your tokens here.  

## Docker
Build an image: `docker build -t tsuki .`  
Run: `docker-compose up -d`  

## Manually
Set up venv: `python3 -m venv env`  
Activate: `source env/bin/activate`  
Install requirements: `pip install -r requirements.txt`  
Install postgresql, redis: `sudo apt install postgresql redis`  
Run postgresql script to init database: `su postgres -c "psql -f {this_directory}/docker.sql"`  
Run: `python3 main.py`
