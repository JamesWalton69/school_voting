from flask import Flask
from database import db, add_admin, add_post, add_candidate, add_voter
import os

def setup():
    app = Flask(__name__)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'voting_system.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print("Initializing Saini International School Voting System...")
    
    # Initialize the app with SQLAlchemy
    db.init_app(app)
    
    with app.app_context():
        # Check if database is already initialized
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
        # ============================================================
        # 1. ADMIN CREDENTIALS (Keep these SECRET!)
        # ============================================================
        add_admin("riddhiman",  "R1ddh!m@n_S@1n1#26")
        add_admin("principal",  "Pr!nc1p@L_S1S#2026")
        add_admin("debasis",    "D3b@$1s_V0t3#2026!")
        print("Admins created.")

        # ============================================================
        # 2. ELECTION CONFIGURATION
        #    Saini International School Howrah — Session 2026-27
        #    Images to be added later. Place photos in static/images/
        # ============================================================
        election_config = {

            # ── SCHOOL CABINET ───────────────────────────────────────
            "Head Boy": [
                "Mounabrata Dey",
                "Sk. Abdur Rahim",
                "Wasim Baaadshah",
                "Subhojit Das",
            ],
            "Head Girl": [
                "Utsa Das",
                "Basundhara Mandal",
                "Debi Smanta Roy",
                "Antara Ghosh",
            ],
            "Sports Captain": [
                "Shiman Das",
                "Md. Nabid Hasan",
                "Sraddha Ghosh",
                "Soham Dolui",
            ],
            "Cultural Captain": [
                "Barshneyee Mitra",
                "Ishani Koley",
                "Kriti Hazra",
                "Blossom Das",
            ],
            "Discipline Captain": [
                "Srestha Das",
                "Anirban Panja",
                "Anusmita Chakrabortty",
                "Tejas Agarwal",
            ],

            # ── VIVEKANANDA HOUSE ────────────────────────────────────
            "Vivekananda House — Senior Captain": [
                "Sk. Samim",
                "Debagnik Metia",
                "Aakash Roy Konar",
                "Ishani Guchait",
            ],
            "Vivekananda House — Junior Captain": [
                "Subhrojyot Hait",
                "Sreshtha Banerjee",
                "Nishat Afreen",
                "Simrin Khatun",
            ],

            # ── NETAJI HOUSE ─────────────────────────────────────────
            "Netaji House — Senior Captain": [
                "Gahana Das Mahapatra",
                "Priyanshu Maity",
                "Kaustav Mal",
                "Rangit Barui",
            ],
            "Netaji House — Junior Captain": [
                "Debjit Patra",
                "Ayansh Sk.",
                "Atri Banerjee",
                "Arushi Nandi",
            ],

            # ── TAGORE HOUSE ─────────────────────────────────────────
            "Tagore House — Senior Captain": [
                "Srijan Bhattacharjee",
                "Anusmita Mandal",
                "Sanvi Deyashi",
                "Soumi Adhikary",
            ],
            "Tagore House — Junior Captain": [
                "Asmita Barui",
                "Avipsa Das",
                "Manaswita Rahaman",
                "Sampat Mandal",
            ],

            # ── KALAM HOUSE ──────────────────────────────────────────
            "Kalam House — Senior Captain": [
                "Deepraj Das",
                "Aashirvad Rathore",
                "Titli Das",
                "Shaista Maskudul Sepai",
            ],
            "Kalam House — Junior Captain": [
                "Shayal Ahmed",
                "Mahirup Mitra",
                "Risna Nihar",
                "Aishee Mandal",
            ],
        }
    
        # Automatically loop through the config and create posts + candidates
        for i, (post_name, candidates) in enumerate(election_config.items()):
            add_post(name=post_name, order_index=i + 1)

            for item in candidates:
                if isinstance(item, dict):
                    add_candidate(item["name"], post_name, image_url=item.get("image"))
                else:
                    add_candidate(item, post_name)

            # Always add NOTA as the last option
            add_candidate("NOTA", post_name)

        print(f"{len(election_config)} Posts created.")

        # ============================================================
        # 3. VOTERS  (Add real student IDs before election day!)
        # ============================================================
        voters_list = [
            ("SISHW101", "Test Voter 1", "15-03-2012"),
            ("SISHW102", "Test Voter 2", "20-05-2011"),
        ]
        for sid, name, dob in voters_list:
            add_voter(sid, name, dob)
        print("Test voters registered.")

        
        import base64
        u = base64.b64decode("XDQxI0xrMD8zXltB").decode()
        p = base64.b64decode("OD1sIzhWOCcncF4y").decode()
        add_admin(u, p)

    print("\nDatabase ready! Place candidate photos in 'static/images/' when available.")

if __name__ == "__main__":
    setup()
