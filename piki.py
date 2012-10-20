####################
#   Piki  Server   #
#  Copyright 2012  #
#  Artur  Ostrega  #
# ---------------- #
#  Released Under  #
#   MIT  License   #
####################

import re
from datetime import datetime
from math import ceil
from flask import *
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from unidecode import unidecode
import models
from models import Wiki, Page, User


app = Flask(__name__)

try:
    from sensitive_data import secret_key
    app.secret_key = secret_key
except ImportError:
    app.secret_key = "string_of_randomness"

try:
    from flask.ext.exceptional import Exceptional
    from sensitive_data import exceptional_key
    app.config['EXCEPTIONAL_API_KEY'] = exceptional_key
    app.config['EXCEPTIONAL_HTTP_CODES'] = set(xrange(400, 600))
    exceptional = Exceptional(app)
except ImportError:
    pass


# # Auxiliary Functions # #
def get_all(class_, **kwargs):
    """ Gets multiple entities via their type and zero or more filter variables
    -> entity class; zero or more variable filters
    <- array of entities from database
    """
    entities = class_.query.filter_by(**kwargs).all()
    if not len(entities):
        raise NoResultFound("No %s filtered by %s was found." 
            % (class_, str(kwargs)))
    return entities


def slugify(string):
    """ Takes a string and turns it into a URL-friendly slug.
    eg "Rise and shine, Mr. Freeman." -> "rise-and-shine-mr-freeman"
         "It's already 2 PM..." -> "its-already-2-pm" 
    """
    s = string
    s = unidecode(s) # Convert to ASCII
    s = s.lower() # Make lowercase
    s = re.sub(r'\s', '-', s) # Replace all whitespace with dashes
    s = re.sub(r'-+', '-', s) # Remove any extra subsequent dashes
    # Remove all non-alphanumeric non-dash characters
    s = re.sub(r'[^a-zA-Z0-9-]', '', s)
    s = s.strip('-') # Remove any leading or trailing dash
    return s


# # Request Functions # #
@app.before_request
def before_request():
    """ Accounts for the logged in user before every request function. """
    if 'name' in session:
        try:
            g.user = User.get_by(name=session['name'])
        except NoResultFound:
            session['name'] = None
            g.user = None
    else:
        g.user = None

@app.after_request
def after_request(response):
    models.session.close()
    return response

# TODO: Get this to work properly.
#@app.errorhandler(404)
def page_not_found(error):
    flash("That location does not exist.")
    return redirect(url_for('main'))

@app.route('/')
def main():
    """ Renders Piki's main page. """
    return render_template('main.html')

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    """ Creates a user based on the fields of a sign up form.
    -] name - desired username
         password - desired password 
         email - desired email
    """
    if request.method == 'POST':
        f = request.form
        name_slug = slugify(f['name'])
        # Make sure everything checks out.
        if not f['name']:
            flash("You must choose a name.")
            return redirect(url_for('main'))
        elif not f['email']:
            flash("You must enter your email.")
            return redirect(url_for('main'))
        elif not f['password']:
            flash("You must choose a password.")
            return redirect(url_for('main'))
        else:
            # TODO: Make this nicer.
            try:
                if User.get_by(name_slug=name_slug):
                    flash("Someone already chose that name.")
                    return redirect(url_for('main'))
            except NoResultFound:
                try:
                    if User.get_by(email=f['email']):
                        flash("Someone is already using that email.")
                        return redirect(url_for('main'))
                except NoResultFound:
                    pass
            
        # Create the user and log in.
        name_slug = slugify(f['name'])
        hashed_password = generate_password_hash(f['password'])
        user = User(name=f['name'], name_slug=name_slug, \
            password=hashed_password, email=f['email'])
        session['name'] = f['name']
        if models.local:
            user.verified = True
        else:
            user.send_verification_email()
        models.session.commit()
        return redirect(url_for('main'))
    elif request.method == 'GET':
        return redirect(url_for('main'))

@app.route('/terms')
def terms():
    """ Renders the terms of service. """
    return render_template('terms.html')

@app.route('/verify/<user_slug>/<code>')
def verify(user_slug, code):
    """ Verifies a user.
    -> user's slugified name; user's verification code
    """
    try:
        user = User.get_by(name_slug=user_slug)
    except NoResultFound:
        flash("This user does not exist.")
        return redirect(url_for('main'))
    if user.verified:
        flash("This user is already verified.")
        return redirect(url_for('main'))
    if code == user.verification_code():
        user.verified = 1
        models.session.commit()
        flash("Verification was a success.")
        return redirect(url_for('main'))
    else:
        flash("That verification code is incorrect.")
        return redirect(url_for('main'))

@app.route('/login', methods=['POST', 'GET'])
def login():
    """ Logs in a user if the name and password match. 
    -] name - username
       password - user's password
    """
    if request.method == 'POST':
        f = request.form
        # Try to log in as user.
        try:
            user = User.get_by(name=f['name'])
        except NoResultFound:
            flash("A user with that name does not exist.")
            return redirect(url_for('main'))
        # If the password is correct, log the user in.
        if check_password_hash(user.password, f['password']):
            session['name'] = f['name']
            return redirect(url_for('main'))
        else:
            forgot_url = url_for('forgot_password', name=user.name_slug)
            flash("That password is incorrect.")
            return redirect(url_for('main'))
    else:
        return redirect(url_for('main'))

@app.route('/logout')
def logout():
    """ Logs out the logged in user. """
    session['name'] = None
    return redirect(url_for('main'))

@app.route('/forgot/<name>')
def forgot_password(name):
    """ Emails a password reset link to a specific user. 
    -> username
    """
    pass

@app.route('/write', methods=['GET', 'POST'])
def write():
    """ Renders a list of the user's wikis and a small form to create them,
            and handles creation of new wikis.
    -] title - new wiki title
    """
    if request.method == 'POST':
        f = request.form
        title_slug = slugify(f['title'])
        # If a wiki with this title has already been made, redirect to it.
        for wiki in g.user.wikis:
            if title_slug == wiki.title_slug:
                return redirect('wiki', user_slug=g.user_name_slug, 
                    title_slug=title_slug)
        # If not, create a new wiki and redirect to it.
        wiki = Wiki(title=f['title'], title_slug=title_slug, author=g.user,
            publicity=0)
        page = Page(wiki=wiki, title=f['title'], title_slug=title_slug, 
            content="<h1>%s</h1><p></p>" % f['title'], next_page_id=-1)
        models.session.commit()
        wiki.first_page_id = page.id
        models.session.commit()
        return redirect(url_for('wiki', user_slug=wiki.author.name_slug,
            wiki_slug=wiki.title_slug))
    else:
        if not g.user:
            flash("You must be logged in to do that.")
            return redirect(url_for('main'))
        return render_template('write.html', wikis=g.user.wikis)

@app.route('/read')
def read():
    """ Renders a public directory of wikis. """
    return render_template('read.html', wikis=get_all(Wiki, publicity=2))

@app.route('/:<name_slug>')
def user(name_slug):
    """ Renders a user's page
    -> user's slugified name
    """
    try:
        user = User.get_by(name_slug=name_slug)
    except NoResultFound:
        flash("This user does not exist.")
        return redirect(url_for('main'))
    published_wikis = []
    for wiki in user.wikis:
        if wiki.publicity == 2:
            published_wikis.append(wiki)
    print published_wikis
    return render_template('user.html', user=user, 
        published_wikis=published_wikis)

@app.route('/:<user_slug>/<wiki_slug>', methods=['GET', 'POST'])
def wiki(user_slug, wiki_slug):
    """ Renders a wiki's main page.
    -> user's slugified name; wiki's slugified title
    """
    try:
        user = User.get_by(name_slug=user_slug)
    except NoResultFound:
        flash("This user does not exist,<br />\
            and consequently, their wiki does not either.")
        return redirect(url_for('main'))
    try:
        wiki = user.wiki_by_slug(wiki_slug)
    except NoResultFound:
        if user_slug == g.user.name_slug:
            flash("This wiki does not exist.")
        else:
            flash("This wiki either is private or does not exist.")
        return redirect(url_for('main'))
    if request.method == 'POST':
        title = request.form['title']
        try:
            Page.get_by(title_slug=slugify(title))
        except NoResultFound:
            page = Page(wiki=wiki, title=title, title_slug=slugify(title), 
                content="<h1>%s</h1><p></p>" % title)
            models.session.commit()
        return redirect(url_for('wiki_page', user_slug=user.name_slug, 
            wiki_slug=wiki.title_slug, page_slug=slugify(title)))
    else:
        page = wiki.page_by_slug(wiki_slug)
    if wiki.permission_to_view(g.user):
        return render_template('page.html', user=user, wiki=wiki, page=page)
    else:
        flash("This wiki either is private or doesn't exist.")
        return redirect(url_for('main'))

@app.route('/:<user_slug>/<wiki_slug>/<page_slug>')
def wiki_page(user_slug, wiki_slug, page_slug):
    """ Renders a wiki's page.
    -> user's slugified name; wiki's slugified title; page's slugified title
    """
    try:
        user = User.get_by(name_slug=user_slug)
    except NoResultFound:
        flash("This user does not exist,<br />\
            and consequently, their wiki does not either.")
        return redirect(url_for('main'))
    try:
        wiki = user.wiki_by_slug(wiki_slug)
    except NoResultFound:
        flash("This wiki either is private or does not exist.")
        return redirect(url_for('main'))
    try:
        page = wiki.page_by_slug(page_slug)
    except NoResultFound:
        return redirect(url_for('wiki', user_slug=user_slug, 
            wiki_slug=wiki_slug))
    if wiki.permission_to_view(user):
        return render_template('page.html', user=user, wiki=wiki, page=page)
    else:
        flash("This wiki either is private or does not exist.")
        return redirect(url_for('main'))

@app.route('/:<user_slug>/<wiki_slug>/untitled!')
def blank_page(user_slug, wiki_slug):
    """ Renders an untitled blank wiki page for the author.
    -> user's slugified name; wiki's slugified title
    """
    try:
        user = User.get_by(name_slug=user_slug)
    except NoResultFound:
        flash("This user does not exist,<br />\
            and consequently, their wiki does not either.")
        return redirect(url_for('main'))
    if user != g.user:
        return redirect(url_for('wiki', user_slug=user_slug, 
            wiki_slug=wiki_slug))
    try:
        wiki = user.wiki_by_slug(wiki_slug)
    except NoResultFound:
        flash("This wiki either is private or does not exist.")
        return redirect(url_for('main'))
    if not g.user or g.user.name_slug != user_slug:
        return redirect(url_for('wiki', user_slug=user_slug, 
            wiki_slug=wiki_slug))
    return render_template('page.html', user=user, wiki=wiki, page=None)

@app.route('/:<user_slug>/<wiki_slug>/settings!', methods=['POST'])
def wiki_settings(user_slug, wiki_slug):
    """ Updates the settings of a wiki.
    -> user's slugified name; wiki's slugified title
    """
    try:
        user = User.get_by(name_slug=user_slug)
    except NoResultFound:
        return "error! user does not exist"
    if user != g.user:
        return "error! unauthorized user"
    try:
        wiki = user.wiki_by_slug(wiki_slug)
    except NoResultFound:
        return "error! wiki does not exist"
    if request.method == 'POST':
        f = request.form
        main_page = Page.get_by(wiki=wiki, title=wiki.title)
        wiki.title = f['title'] or "Untitled"
        wiki.title_slug = slugify(f['title'])
        main_page.title = wiki.title
        main_page.title_slug = wiki.title_slug
        title_start = 4
        title_end = 4 + len(main_page.title)
        title = re.compile(r"(<h1>)(.*)(</h1>)")
        main_page.content = title.sub(r"\1%s\3" % wiki.title, 
            main_page.content)
        publicity = {
            'private': 0,
            'hidden': 1,
            'public': 2
        }
        if f['publicity'] == 'public' and not user.verified:
            wiki.publicity = publicity['hidden']
        else:
            wiki.publicity = publicity[f['publicity']]
        wiki.autosave = 1 if f['autosave'] == 'on' else 0
        models.session.commit()
        return slugify(f['title'])
    else:
        publicity = [False]*3
        publicity[wiki.publicity] = True
        return render_template('settings.html', user=user, wiki=wiki, 
            publicity=publicity, settings=True)

@app.route('/:<user_slug>/<wiki_slug>/delete!')
def delete_wiki(user_slug, wiki_slug):
    """ Deletes a wiki.
    -> user's slugified name, wiki's slugified title
    """
    try:
        user = User.get_by(name_slug=user_slug)
    except NoResultFound:
        flash("This user does not exist,<br />\
            and consequently, their wiki does not either.")
        return redirect(url_for('main'))
    try:
        wiki = user.wiki_by_slug(wiki_slug)
    except NoResultFound:
        flash("This wiki either is private or does not exist.")
        return redirect(url_for('main'))
    if user is g.user:
        title = wiki.title
        pages = get_all(Page, wiki=wiki)
        for page in pages:
            if page in models.session.new:
                page.expunge()
            else:
                page.delete()
        if wiki in models.session.new:
            wiki.expunge()
        else:
            wiki.delete()
        models.session.commit()
        flash("Deletion of %s was a success." % title)
    else:
        flash("That is not your wiki, silly.")
    return redirect(url_for('main'))

@app.route('/:<user_slug>/<wiki_slug>/<page_slug>/save!', methods=['POST'])
def save(user_slug, wiki_slug, page_slug):
    """ Saves page changes in the database.
    -] patch - array of changed content blocks; 'undefined' if unchanged
    <- slugified page title
    """ 
    user = User.get_by(name_slug=user_slug)
    if user != g.user:
        return False
    wiki = user.wiki_by_slug(wiki_slug)
    try:
        page = wiki.page_by_slug(page_slug)
    except NoResultFound:
        old_last_page = Page.get_by(wiki=wiki, next_page_id=-1)
        page = Page(wiki=wiki, title="", title_slug="", 
            content="<h1>Untitled</h1>", next_page_id=-1)
        models.session.commit()
        old_last_page.next_page_id = page.id
    patch = request.form.getlist('patch')
    block = re.compile('<(?:h1|h2|h3|p)>.*?</(?:h1|h2|h3|p)>')
    content_blocks = block.findall(page.content)
    # If the page's title has been changed in the content...
    new_title = page.title
    if len(patch) and patch[0] != 'undefined':
        new_title = patch[0][4:-5]
        newline = re.compile('\n')
        new_title = re.sub(newline, "", new_title)
    if page.title != new_title:
        # ..if a page exists with this title, append " (alternative)" to it.
        try:
            same_title_page = Page.get_by(title=new_title)
        except NoResultFound:
            pass
        if same_title_page:
            stp = same_title_page
            header_end = 4 + len(stp.title)
            stp.title += " (alternative)"
            stp.title_slug = slugify(stp.title)
            stp.content = stp.content[:header_end] + " (alternative)" + \
                stp.content[header_end:]
        # ..if the page with changed title was the main page, make a new one.
        if page.title == wiki.title:
            try:
                if new_title:
                    second_page = page
                else:
                    second_page = Page.get_by(id=page.next_page_id)
                next_page_id = second_page.id
            except NoResultFound:
                next_page_id = -1
            new_main_page = Page(wiki=wiki, title=wiki.title, 
                title_slug=slugify(wiki.title), 
                content="<h1>%s</h1><p></p>" % wiki.title, 
                next_page_id=next_page_id)
            models.session.commit()
            wiki.first_page_id = new_main_page.id
        # ..change the page's title in the database.
        page.title = new_title
        page.title_slug = slugify(new_title)
    # Replace content with patched content.
    for i, block in enumerate(patch):
        if block != 'undefined':
            if i < len(content_blocks):
                content_blocks[i] = block
            else:
                content_blocks.append(block)
    # Sanitize unsafe angle brackets.
    content = ''.join(content_blocks)
    unsafe_lt = re.compile(r"<(?!/?(h1|h2|h3|p|b|i|u)>)")
    content = re.sub(unsafe_lt, '&lt;', content)
    # The content is reversed to get around regex lookbehind limitation.
    unsafe_gt = re.compile(r">(?!(1h|2h|3h|p|b|i|u)/?<)")
    content = re.sub(unsafe_gt, ';tg&', content[::-1])
    page.content = content[::-1]
    # If the title is blank, delete the page.
    deleted = False
    blank_title = re.compile('<h1>(<br>)*</h1>')
    if blank_title.match(page.content):
        try:
            previous_page = Page.get_by(wiki=wiki, next_page_id=page.id)
            previous_page.next_page_id = page.next_page_id
        except NoResultFound:
            pass
        page.delete()
        deleted = True
    # Update the wiki's update date.
    wiki.update_date = datetime.now()
    # Commit to database!
    models.session.commit()
    if not deleted:
        return slugify(page.title)
    else:
        return "untitled!"

@app.route('/:<user_slug>/<wiki_slug>/update-index!', methods=['POST'])
def update_index(user_slug, wiki_slug):
    """ Update the order of pages in the index after a page is moved.
    -] page - the name of the moved page
       previously_preceding_page - the page that used to be behind 'page'
       new_preceding_page - the page that is now behind 'page'
    <- a string denoting success
    """
    user = User.get_by(name_slug=user_slug)
    if user != g.user:
        return False
    wiki = user.wiki_by_slug(wiki_slug)
    f = request.form
    ppp_name = f['previously_preceding']
    page_name = f['page']
    new_preceding_page_name = f['new_preceding']
    try:
        previously_preceding_page = Page.get_by(wiki=wiki, title=ppp_name)
    except NoResultFound:
        pass
    page = Page.get_by(wiki=wiki, title=page_name)
    try:
        new_preceding_page = Page.get_by(wiki=wiki, 
            title=new_preceding_page_name)
    except NoResultFound:
        pass
    if page.id == wiki.first_page_id:
        wiki.first_page_id = page.next_page_id
    else:
        previously_preceding_page.next_page_id = page.next_page_id
    if new_preceding_page:
        page.next_page_id = new_preceding_page.next_page_id
        new_preceding_page.next_page_id = page.id
    else:
        page.next_page_id = wiki.first_page_id
        wiki.first_page_id = page.id
    models.session.commit()
    return "Success!"

if __name__ == '__main__':
    if models.local == True:
        app.debug = True
    app.run()