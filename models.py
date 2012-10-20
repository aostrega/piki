####################
#   Piki  Models   #
#  Copyright 2012  #
#  Artur  Ostrega  #
# ---------------- #
#  Released Under  #
#   MIT  License   #
####################

from datetime import datetime
from smtplib import SMTP
from elixir import *
from sqlalchemy.orm.exc import NoResultFound

local = True

def setup():
    if local:
        metadata.bind = "sqlite:///database.sqlite"
    else:
        from sensitive_data import database_url
        metadata.bind = database_url
    setup_all()
    create_all()


class User(Entity):
    name = Field(Unicode(50))
    name_slug = Field(Unicode(50))
    password = Field(Unicode(54))
    email = Field(Unicode(50))
    wikis = OneToMany('Wiki')
    join_date = Field(DateTime, default=datetime.now)
    verified = Field(Boolean, default=False)

    def __repr__(self):
        return '<User "%s">' % self.name

    def wiki_by_slug(self, wiki_slug):
        for wiki in self.wikis:
            if wiki.title_slug == wiki_slug:
                return wiki
        raise NoResultFound("Wiki with slug '%s' by '%s' was not found."
            % (wiki_slug, self))

    def verification_code(self):
        try:
            from sensitive_data import generate_verification_code
            return generate_verification_code(self)
        except ImportError:
            return 4 # guaranteed to be random.

    def send_verification_email(self):
        try:
            email = "pikimailman@gmail.com"
            from sensitive_data import email_password
            password = email_password
        except ImportError:
            email = "???"
            password = "???"
        message = ("From: {0}\n"
            "To: {1}\n"
            "Subject: Piki bids you welcome."
            "\n\n"
            "Thank you for giving Piki a shot, {2}. "
            "I hope you will find it useful."
            "\n\n"
            "Your verification link is " 
            "http://piki.heroku.com/verify/{3}/{4}."
            "\n\n"
            "If you have any questions, or perhaps some feedback, "
            "write an email to skoofoo@gmail.com."
            ).format(email, self.email, self.name, self.name_slug, 
                self.verification_code())

        server = SMTP("smtp.gmail.com:587")
        server.ehlo()
        server.starttls()
        server.login(email, password)
        server.sendmail(email, user.email, message)
        server.quit()


class Wiki(Entity):
    title = Field(Unicode(50), unique=True)
    title_slug = Field(Unicode(50), unique=True)
    pages = OneToMany('Page')
    first_page_id = Field(Integer)
    author = ManyToOne('User')
    publicity = Field(Integer)
    autosave = Field(Integer, default=1)
    creation_date = Field(DateTime, default=datetime.now)
    update_date = Field(DateTime, default=datetime.now)

    def __repr__(self):
        return '<Wiki "%s">' % self.title

    def page_by_slug(self, page_slug):
        for page in self.pages:
            if page.title_slug == page_slug:
                return page
        raise NoResultFound("Page with slug '%s' in '%s' was not found."
            % (page_slug, self))

    def ordered_pages(self):
        pages = []
        pages.append(Page.query.filter_by(id=self.first_page_id).one())
        next_page_id = pages[0].next_page_id
        while next_page_id != -1:
            pages.append(Page.query.filter_by(id=next_page_id).one())
            next_page_id = pages[-1].next_page_id
        return pages

    def permission_to_view(self, user):
        return user == self.author or self.publicity > 0


class Page(Entity):
    wiki = ManyToOne('Wiki')
    title = Field(Unicode(50))
    title_slug = Field(Unicode(50))
    content = Field(UnicodeText, default=u"<h1></h1>")
    next_page_id = Field(Integer)

    def __repr__(self):
        return '<Page "%s">' % self.title

setup()