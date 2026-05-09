from flask import Flask
from database import db, init_db, add_admin, add_post, add_candidate, add_voter
import os

def setup():
    app = Flask(__name__)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'voting_system.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print("Initializing Multi-Post Voting System with IMAGES...")
    
    # Initialize the app with SQLAlchemy
    db.init_app(app)
    
    with app.app_context():
        # Check if database is already initialized
        # Use try-except in case tables don't exist yet
        try:
            from database import Post
            if Post.query.first():
                print("Database already contains data. Skipping re-initialization to protect votes.")
                return
        except:
            pass

        print("Creating new database schema...")
        db.drop_all()
        db.create_all()
    
    with app.app_context():
        # 1. Add Admins
        add_admin("riddhiman", "riddhiman123")
        add_admin("principal", "principal123")
        print("Admins created.")

        # 2. DEFINE YOUR ELECTION HERE
        # Format: "Post Name": [ {"name": "Candidate Name", "image": "filename.jpg"}, ... ]
        # Images should be placed in 'static/images/' folder.
        election_config = {
            "Head Boy": [
                {"name": "Arjun Singh", "image": "arjun.png"},
                {"name": "Kabir Mehra", "image": "kabir.png"}
            ],
            "Head Girl": [
                {"name": "Ishani Bose", "image": "ishani.png"},
                {"name": "Meera Iyer", "image": "meera.png"}
            ],
            "Sports Head Boy": [
                {"name": "Rohan Das", "image": "rohan.png"},
                {"name": "Yash Wardhan", "image": "yash.png"}
            ],
            "Sports Head Girl": [
                {"name": "Sana Khan", "image": "sana.png"},
                {"name": "Ananya Sharma", "image": "ananya.png"}
            ],
            # You can also just provide strings if you don't have images for some posts yet
            "Discipline Head Boy": ["Aditya Roy", "Sahil Verma"],
            "Discipline Head Girl": ["Riya Gupta", "Tanvi Shah"],
            
            # House posts (Fill these with real names/images as needed)
            "Blue House Head Senior Boy": ["B-Senior Boy 1", "B-Senior Boy 2"],
            "Blue House Head Senior Girl": ["B-Senior Girl 1", "B-Senior Girl 2"],
            "Blue House Junior Boy": ["B-Junior Boy 1", "B-Junior Boy 2"],
            "Blue House Junior Girl": ["B-Junior Girl 1", "B-Junior Girl 2"],
            
            "Yellow House Head Senior Boy": ["Y-Senior Boy 1", "Y-Senior Boy 2"],
            "Yellow House Head Senior Girl": ["Y-Senior Girl 1", "Y-Senior Girl 2"],
            "Yellow House Junior Boy": ["Y-Junior Boy 1", "Y-Junior Boy 2"],
            "Yellow House Junior Girl": ["Y-Junior Girl 1", "Y-Junior Girl 2"],
            
            "Red House Head Senior Boy": ["R-Senior Boy 1", "R-Senior Boy 2"],
            "Red House Head Senior Girl": ["R-Senior Girl 1", "R-Senior Girl 2"],
            "Red House Junior Boy": ["R-Junior Boy 1", "R-Junior Boy 2"],
            "Red House Junior Girl": ["R-Junior Girl 1", "R-Junior Girl 2"],
            
            "Green House Head Senior Boy": ["G-Senior Boy 1", "G-Senior Boy 2"],
            "Green House Head Senior Girl": ["G-Senior Girl 1", "G-Senior Girl 2"],
            "Green House Junior Boy": ["G-Junior Boy 1", "G-Junior Boy 2"],
            "Green House Junior Girl": ["G-Junior Girl 1", "G-Junior Girl 2"]
        }

        # Automatically loop through the config
        for i, (post_name, candidates) in enumerate(election_config.items()):
            add_post(name=post_name, order_index=i+1)
            
            for item in candidates:
                if isinstance(item, dict):
                    # Has name and image
                    add_candidate(item["name"], post_name, image_url=item.get("image"))
                else:
                    # Just name
                    add_candidate(item, post_name)
            
            # Always add NOTA as the last option
            add_candidate("NOTA", post_name)
            
        print(f"{len(election_config)} Posts created with image support.")

        # 3. Add Voters
        voters_list = [("101", "Sagnik"), ("102", "Soumya")]
        for sid, name in voters_list:
            add_voter(sid, name)
        print("Voters registered.")

    print("\nDatabase is ready with image support! Place photos in 'static/images/'.")

if __name__ == "__main__":
    setup()
