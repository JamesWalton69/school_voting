import os
import secrets
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import (
    db, init_db, verify_admin, verify_voter, register_vote,
    add_voter, get_all_voters_status, reset_all_data,
    get_all_posts, get_post_by_id, get_candidates_for_post,
    get_next_post_for_voter, get_results_for_post, get_voter_progress,
    lock_voter_session, verify_voter_session, unlock_voter_session,
    force_unlock_all_sessions
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'voting_system.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)

# --- Middleware: CSRF Protection ---
@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get('csrf_token', None)
        form_token = request.form.get('csrf_token', None)
        if not token or token != form_token:
            flash("Session expired. Please try again.", "error")
            return redirect(request.url)

def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token


# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')


@app.route('/vote', methods=['GET', 'POST'])
def vote_login():
    """Student ID Login for Voting"""
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip().upper()
        
        if not student_id:
            flash("Please enter your Student ID.", "error")
            return redirect(url_for('vote_login'))
            
        student_name = verify_voter(student_id)
        if not student_name:
            flash("Student ID not found. Contact the Admin.", "error")
            return redirect(url_for('vote_login'))
        
        # --- SESSION LOCKING: Prevent dual login ---
        token, error = lock_voter_session(student_id)
        if error:
            flash(error, "error")
            return redirect(url_for('vote_login'))
            
        # Store securely in session
        session['voter_id'] = student_id
        session['voter_name'] = student_name
        session['voter_token'] = token  # Unique session lock token
        
        flash(f"Welcome, {student_name}!", "success")
        return redirect(url_for('vote_router'))
        
    return render_template('vote.html', step='login')


@app.route('/vote/router')
def vote_router():
    """Determines the next post to vote for, or finishes the process."""
    if 'voter_id' not in session:
        return redirect(url_for('vote_login'))
    
    # Verify session lock is still valid
    if not verify_voter_session(session['voter_id'], session.get('voter_token', '')):
        session.pop('voter_id', None)
        session.pop('voter_name', None)
        session.pop('voter_token', None)
        flash("Your session has expired or was taken over. Please login again.", "error")
        return redirect(url_for('vote_login'))
        
    student_id = session['voter_id']
    next_post = get_next_post_for_voter(student_id)
    
    if next_post:
        return redirect(url_for('cast_vote', post_id=next_post.id))
    else:
        # All posts voted for - unlock the session
        unlock_voter_session(student_id)
        return redirect(url_for('vote_success'))


@app.route('/vote/post/<int:post_id>', methods=['GET', 'POST'])
def cast_vote(post_id):
    """Voting interface for a specific post."""
    if 'voter_id' not in session:
        return redirect(url_for('vote_login'))
    
    # Verify session lock
    if not verify_voter_session(session['voter_id'], session.get('voter_token', '')):
        session.pop('voter_id', None)
        session.pop('voter_name', None)
        session.pop('voter_token', None)
        flash("Your session has expired. Please login again.", "error")
        return redirect(url_for('vote_login'))
        
    student_id = session['voter_id']
    
    # Ensure they aren't skipping around
    expected_next_post = get_next_post_for_voter(student_id)
    if not expected_next_post or expected_next_post.id != post_id:
        return redirect(url_for('vote_router'))

    post = get_post_by_id(post_id)
    candidates = get_candidates_for_post(post_id)
    voted_ids, total_posts = get_voter_progress(student_id)
    progress_text = f"Post {len(voted_ids) + 1} of {total_posts}"
    progress_pct = (len(voted_ids) / total_posts) * 100

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        if not candidate_id:
            flash("Please select a candidate.", "error")
            return redirect(url_for('cast_vote', post_id=post_id))
            
        if register_vote(student_id, post_id, candidate_id, request.remote_addr):
            # Success, go to next post
            return redirect(url_for('vote_router'))
        else:
            flash("An error occurred. You may have already voted for this post.", "error")
            return redirect(url_for('vote_router'))

    # --- RANDOMIZE CANDIDATE ORDER ---
    # Separate NOTA from the rest, shuffle the real candidates, then put NOTA at the end
    nota = [c for c in candidates if c.name == 'NOTA']
    real_candidates = [c for c in candidates if c.name != 'NOTA']
    random.shuffle(real_candidates)
    shuffled_candidates = real_candidates + nota

    return render_template('vote.html', 
                           step='voting',
                           post=post,
                           candidates=shuffled_candidates,
                           student_name=session.get('voter_name'),
                           progress_text=progress_text,
                           progress_pct=progress_pct)


@app.route('/vote/success')
def vote_success():
    """Final success page when all votes are cast"""
    if 'voter_id' in session:
        # Unlock the voter session and clear browser session
        unlock_voter_session(session['voter_id'])
        session.pop('voter_id', None)
        session.pop('voter_name', None)
        session.pop('voter_token', None)
    return render_template('success.html')


# ==================== ADMIN ROUTES ====================

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if verify_admin(username, password):
            session['admin_logged_in'] = True
            session['admin_user'] = username
            flash("Welcome, Principal! You are now logged in.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password.", "error")
    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard"""
    if not session.get('admin_logged_in'):
        flash("Please login to access the dashboard.", "error")
        return redirect(url_for('admin_login'))

    voters = get_all_voters_status()
    completed_count = sum(1 for v in voters if v['Status'] == 'Completed')
    pending_count = len(voters) - completed_count
    
    posts = get_all_posts()

    return render_template('dashboard.html',
                           voters=voters,
                           completed_count=completed_count,
                           pending_count=pending_count,
                           posts=posts,
                           admin_user=session.get('admin_user', 'Admin'))


@app.route('/admin/add-voter', methods=['POST'])
def admin_add_voter():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    new_id = request.form.get('student_id', '').strip().upper()
    new_name = request.form.get('student_name', '').strip()
    if add_voter(new_id, new_name):
        flash(f"Voter {new_name} (ID: {new_id}) added successfully!", "success")
    else:
        flash("Failed to add voter. ID may already exist.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/unlock-voter', methods=['POST'])
def admin_unlock_voter():
    """Admin can force-unlock a stuck voter session."""
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    voter_id = request.form.get('voter_id', '').strip().upper()
    if unlock_voter_session(voter_id):
        flash(f"Voter {voter_id} has been unlocked.", "success")
    else:
        flash("Voter not found.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/unlock-all', methods=['POST'])
def admin_unlock_all():
    """Admin can force-unlock ALL stuck voter sessions."""
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    force_unlock_all_sessions()
    flash("All voter sessions have been unlocked.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    if request.form.get('confirm_reset') == 'RESET':
        if reset_all_data():
            flash("All votes have been reset successfully.", "success")
        else:
            flash("Error during reset.", "error")
    else:
        flash("Please type 'RESET' to confirm.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/results')
def admin_results():
    """Results page - shows dropdown to select which post to view"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    posts = get_all_posts()
    selected_post_id = request.args.get('post_id', type=int)
    
    if not selected_post_id and posts:
        selected_post_id = posts[0].id
        
    results = []
    selected_post = None
    total_votes = 0
    winner = None
    is_tie = False
    max_votes = 0
    
    if selected_post_id:
        selected_post = get_post_by_id(selected_post_id)
        results = get_results_for_post(selected_post_id)
        total_votes = sum(res['votes'] for res in results)
        
        if results and total_votes > 0:
            max_votes = results[0]['votes']
            winners = [res['name'] for res in results if res['votes'] == max_votes]
            if len(winners) > 1:
                is_tie = True
                winner = ', '.join(winners)
            else:
                winner = winners[0]

    return render_template('results.html',
                           posts=posts,
                           selected_post=selected_post,
                           results=results,
                           total_votes=total_votes,
                           winner=winner,
                           is_tie=is_tie,
                           max_votes=max_votes)


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_user', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('admin_login'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
