from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import hashlib
import secrets

db = SQLAlchemy()

# --- Models ---

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    order_index = db.Column(db.Integer, nullable=False) # For the wizard flow

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    
    post = db.relationship('Post', backref=db.backref('candidates', lazy=True))

class Voter(db.Model):
    __tablename__ = 'voters'
    id = db.Column(db.String(20), primary_key=True)  # Student ID
    name = db.Column(db.String(100), nullable=False)
    # Session locking: prevents same ID on two computers
    session_token = db.Column(db.String(64), nullable=True)
    session_started_at = db.Column(db.DateTime, nullable=True)

    SESSION_TIMEOUT_MINUTES = 30  # Auto-unlock after 30 min of inactivity

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(20), db.ForeignKey('voters.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # CRITICAL: Ensures one vote per post per voter
    __table_args__ = (db.UniqueConstraint('voter_id', 'post_id', name='_voter_post_uc'),)


# --- Database Functions ---

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

def add_admin(username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if not Admin.query.filter_by(username=username).first():
        new_admin = Admin(username=username, password_hash=password_hash)
        db.session.add(new_admin)
        db.session.commit()
        return True
    return False

def verify_admin(username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    admin = Admin.query.filter_by(username=username).first()
    if admin:
        return admin.password_hash == password_hash
    return False

def add_post(name, order_index):
    if not Post.query.filter_by(name=name).first():
        new_post = Post(name=name, order_index=order_index)
        db.session.add(new_post)
        db.session.commit()
        return True
    return False

def add_candidate(name, post_name, image_url=None):
    post = Post.query.filter_by(name=post_name).first()
    if post:
        new_candidate = Candidate(name=name, post_id=post.id, image_url=image_url)
        db.session.add(new_candidate)
        db.session.commit()
        return True
    return False

def get_all_posts():
    return Post.query.order_by(Post.order_index).all()

def get_post_by_id(post_id):
    return Post.query.get(post_id)

def get_candidates_for_post(post_id):
    candidates = Candidate.query.filter_by(post_id=post_id).all()
    # Also add NOTA for every post dynamically if we want, or add it explicitly during setup.
    # For now, assuming NOTA is added explicitly per post during setup.
    return candidates

def register_vote(student_id, post_id, candidate_id, ip_address=None):
    try:
        # The UniqueConstraint on the Vote table will automatically
        # throw an IntegrityError if the user tries to vote twice for the same post.
        new_vote = Vote(
            voter_id=student_id,
            post_id=post_id,
            candidate_id=candidate_id,
            ip_address=ip_address
        )
        db.session.add(new_vote)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error registering vote: {e}")
        return False

def add_voter(student_id, name):
    student_id = student_id.strip().upper()
    if not Voter.query.get(student_id):
        new_voter = Voter(id=student_id, name=name)
        db.session.add(new_voter)
        db.session.commit()
        return True
    return False

def verify_voter(student_id):
    voter = Voter.query.get(student_id.strip().upper())
    if voter:
        return voter.name
    return None

def lock_voter_session(student_id):
    """Lock a voter to a specific session. Returns (token, error_msg)."""
    voter = Voter.query.get(student_id.strip().upper())
    if not voter:
        return None, 'Voter not found'
    
    # Check if already locked by another session
    if voter.session_token and voter.session_started_at:
        elapsed = datetime.utcnow() - voter.session_started_at
        if elapsed < timedelta(minutes=Voter.SESSION_TIMEOUT_MINUTES):
            return None, f'{voter.name} is already voting on another computer. Please wait or ask the admin to unlock.'
        # Session expired, allow re-lock
    
    # Create new session lock
    token = secrets.token_hex(32)
    voter.session_token = token
    voter.session_started_at = datetime.utcnow()
    db.session.commit()
    return token, None

def verify_voter_session(student_id, token):
    """Check if the given token matches the active session for this voter."""
    voter = Voter.query.get(student_id.strip().upper())
    if not voter or not voter.session_token:
        return False
    if voter.session_token != token:
        return False
    # Check timeout
    if voter.session_started_at:
        elapsed = datetime.utcnow() - voter.session_started_at
        if elapsed >= timedelta(minutes=Voter.SESSION_TIMEOUT_MINUTES):
            return False
    # Refresh the session timer on each action
    voter.session_started_at = datetime.utcnow()
    db.session.commit()
    return True

def unlock_voter_session(student_id):
    """Unlock a voter's session (called on completion or by admin)."""
    voter = Voter.query.get(student_id.strip().upper())
    if voter:
        voter.session_token = None
        voter.session_started_at = None
        db.session.commit()
        return True
    return False

def force_unlock_all_sessions():
    """Admin function: unlock all voter sessions."""
    Voter.query.update({'session_token': None, 'session_started_at': None})
    db.session.commit()

def get_voter_progress(student_id):
    """Returns (voted_post_ids_list, total_posts_count)"""
    voted_posts = db.session.query(Vote.post_id).filter_by(voter_id=student_id).all()
    voted_post_ids = [v[0] for v in voted_posts]
    total_posts = Post.query.count()
    return voted_post_ids, total_posts

def get_next_post_for_voter(student_id):
    voted_post_ids, _ = get_voter_progress(student_id)
    # Get the first post ordered by order_index that the voter HAS NOT voted for
    if voted_post_ids:
        next_post = Post.query.filter(
            ~Post.id.in_(voted_post_ids)
        ).order_by(Post.order_index).first()
    else:
        # Voter hasn't voted for anything yet - return the very first post
        next_post = Post.query.order_by(Post.order_index).first()
    return next_post

def get_results_for_post(post_id):
    # Get candidates and their vote counts for a specific post
    candidates = Candidate.query.filter_by(post_id=post_id).all()
    results = []
    for c in candidates:
        count = Vote.query.filter_by(candidate_id=c.id).count()
        results.append({
            'name': c.name,
            'votes': count,
            'image_url': c.image_url
        })
    
    # Sort by votes descending
    return sorted(results, key=lambda x: x['votes'], reverse=True)

def get_all_voters_status():
    voters = Voter.query.all()
    total_posts = Post.query.count()
    
    result = []
    for v in voters:
        vote_count = Vote.query.filter_by(voter_id=v.id).count()
        
        if vote_count == 0:
            status = 'Not Started'
        elif vote_count == total_posts:
            status = 'Completed'
        else:
            status = f'In Progress ({vote_count}/{total_posts})'
            
        result.append({
            'ID': v.id,
            'Name': v.name,
            'Status': status,
            'VoteCount': vote_count
        })
    return sorted(result, key=lambda x: x['ID'])

def reset_all_data():
    try:
        # Delete all votes
        Vote.query.delete()
        # Also unlock all voter sessions
        force_unlock_all_sessions()
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return False
