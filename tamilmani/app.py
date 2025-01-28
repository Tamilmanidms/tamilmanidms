
# FLASK ATTRIBUTES
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    send_file,
    flash
)
# ENVIRONMENT LOADER
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
# IMAGE BYTES HANDLER
import io

# DATABASE ORM HANDLER
from sqlalchemy import desc


# PAGINATION HANDLER
from flask_paginate import Pagination, get_page_args

# SECURITY HASH PASSWORD HANDLER
from werkzeug.security import check_password_hash, generate_password_hash

# DATABASE MODULE HANDLER ( OUR MODULE )
from .database import db, Contact, Document, Category, ContactInfo, PageInformation,DocumentView,ProfileAbout,Youtube
# **************** .database podu
# AUTHENTICATION AND LOGIN HANDLER
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user,login_required

# FLASK ADMIN HANDLER
from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView, Admin
# NOTE : FORM OPERATION 
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
import tamilmani.firebase as firebase
# *************** tamilmani.
from flask_caching import Cache
from flask_minify import minify
# REDDIS CACHE
# Fetch Upstash Redis credentials from environment variables
kv_url = os.getenv('KV_URL')
kv_rest_api_url = os.getenv('KV_REST_API_URL')
kv_rest_api_token = os.getenv('KV_REST_API_TOKEN')
kv_read_only_token = os.getenv('KV_REST_API_READ_ONLY_TOKEN')




app = Flask(__name__, template_folder='template')

# Initialize Flask-Minify for global minification (optional, if needed for all pages)
minify(app=app, html=True, js=True)

# Configure Flask-Caching with Redis
app.config['CACHE_TYPE'] = 'RedisCache'
app.config['CACHE_REDIS_URL'] = kv_url  # Use the secure Redis URL
app.config['CACHE_DEFAULT_TIMEOUT'] = 60*60*12  # Cache timeout in seconds
cache = Cache(app)
# Configuration
# app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///project.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# INITIALIZE DB
db.init_app(app)


login = LoginManager(app)



'''
ADMIN SECTION

'''
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# RE CONFIGURE MODELVIEW
class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class MyAdminIndexView(AdminIndexView):
    @login_required
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))



# ADMIN INITIALIZING
db_admin = Admin(app, name='Dashboard', template_mode='bootstrap3',index_view=MyAdminIndexView())

# NOTE : add_view used to add db_admin pannel inside model based CRUD operations.

db_admin.add_view(DocumentView(Document, db.session))
db_admin.add_view(ModelView(Category, db.session))
# db_admin.add_view(ModelView(Contact, db.session))
db_admin.add_view(ModelView(PageInformation, db.session))
db_admin.add_view(ModelView(ContactInfo, db.session))
db_admin.add_view(ModelView(ProfileAbout, db.session))
db_admin.add_view(ModelView(Youtube, db.session))
# db_admin.add_view(MyModelView(User, db.session))




@login.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
'''
END OF ADMIN SECTION

'''


# HOME PAGE

@app.route('/')
@cache.cached()  # Cache this route for 60 seconds
def home():
    page_data = PageInformation.query.first()
    contact_info_data = ContactInfo.query.all()
    categories = Category.query.all()
    youtube =   Youtube.query.order_by(desc(Youtube.id)).limit(4).all()
    response = render_template('index.html', categories=categories, contact=contact_info_data, page_info=page_data,youtube=youtube)
    
    return response



# THANKYOU FOR CONTACT US
@cache.cached() 
@app.route('/thank_you')
def thank_you():
    return render_template("thank_you_page.html")


# DOCUMENT GETTING
def get_documents(page, per_page, category_id=None, search_term=None):
    query = Document.query
    if category_id:
        query = query.filter_by(category_id=category_id)

    print("sear term called")
    if search_term:
        query = query.filter(Document.document_filename.ilike(f'%{search_term}%'))
        print("query = ",query)
    return query.paginate(page=page, per_page=per_page, error_out=False)

# YOUTUBE URL GETTING
def get_urls(page=1, per_page=10, search_term=None):
    
    if search_term:
        res = Youtube.query.filter(Youtube.title.ilike(f'%{search_term}%'))
      
    
    # Apply pagination to the filtered (or unfiltered) query
    pagination =  Youtube.query.paginate(page=page, per_page=per_page, error_out=False)
    
    return pagination

# DOWNLOAD PAGE
@app.route('/download_page')
@cache.cached() 
def download_page():
    category_id = request.args.get('category_id', type=int)
    page = request.args.get('page',1,type=int)
    per_page = request.args.get('per_page',9,type=int)
    documents = get_documents(page, per_page, category_id)

    
    return render_template('download_page.html', documents=documents.items, pagination=documents,  current_category=category_id)

# DOWNLOAD PAGE

@app.route('/youtube_page')
@cache.cached() 
def youtube_page():
    
    page = request.args.get('page',1,type=int)
    per_page = request.args.get('per_page',9,type=int)
   
    # Note : documents_query holds items and pagination object
    source_query = get_urls(page,per_page,search_term=None)
    print('source : ',source_query)
   
    return render_template('youtube_page.html', documents=source_query.items, pagination=source_query, current_category=None)

# SEARCH ROUTE
@app.route('/search')
def search_documents():
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return render_template('macros/document_component.html', documents=None)
    
    documents=get_documents(1,2,search_term=search_term)
    
    return render_template('macros/document_component.html', documents=documents)


# SEARCH ROUTE
@app.route('/youtube_search')
def youtube_search():
    search_term = request.args.get('q', '').strip()
    print("search term = ",search_term)
    if not search_term:
        return render_template('macros/youtube_component.html', documents=None)
    documents=get_urls(search_term=search_term)
    print("youtube search results = ",documents)


    
    return render_template('macros/youtube_component.html', documents=documents)

# DOCUMENT GETTING WITH ID FOR DOWNLOAD
@app.route('/get_document', methods=['GET'])
def get_document():
    document_id = request.args.get('document_id')
    if not document_id:
        return jsonify({'error': 'No document ID provided'}), 400
    
    document_detail = Document.query.get(document_id)
    document = firebase.get_file(document_detail.document_filename)
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    return redirect(document)



# CONTACT US PAGE TO DB ROUTE
@app.route('/submit_contact_form', methods=['POST'])
def submit_contact_form():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    return render_template("thank_you_page.html")
   
    

# NOTE : PROFILE ABOUT PAGE
# -------------------------
@app.route('/about')
@cache.cached() 
def profile():

    profiles = ProfileAbout.query.all()
    
    formatted_profiles = []
    

    for profile in profiles:
        formatted_profile = {
            'title': profile.title,
            # Replace \n with <br> tags
            'detail': profile.detail.split('/n')
        }
        print(formatted_profile)
        formatted_profiles.append(formatted_profile)
    
    return render_template('about.html', profiles=formatted_profiles)


# NOTE : LOGIN FORM
# ------------------
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4, max=25)])
    submit = SubmitField('Login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)



# LOGOUT ROUTE
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home')) 

@app.route('/settup')
def settup():
    with app.app_context():
        db.create_all()
        print("Database Created Successfully")
        if not User.query.filter_by(username='tm').first():
            new_user = User(username=os.getenv('ADMIN_USERNAME'), password = generate_password_hash(os.getenv('ADMIN_PASSWORD')))
            db.session.add(new_user)
            db.session.commit()
    return "Success"
from flask import Response
from datetime import datetime

@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    """Generate a dynamic sitemap.xml file for the website."""
    # Base URL for the sitemap (replace with your domain)
    base_url = request.url_root.rstrip('/')
    
    # Define static routes
    static_urls = [
        {"loc": f"{base_url}/", "lastmod": datetime.now().strftime("%Y-%m-%d")},
        {"loc": f"{base_url}/about", "lastmod": datetime.now().strftime("%Y-%m-%d")},
        {"loc": f"{base_url}/youtube_page", "lastmod": datetime.now().strftime("%Y-%m-%d")},
        {"loc": f"{base_url}/download_page", "lastmod": datetime.now().strftime("%Y-%m-%d")},
    ]
    
    # Dynamically add URLs from the database (Categories, Documents, etc.)
    dynamic_urls = []
    
    # Categories
    categories = Category.query.all()
    for category in categories:
        dynamic_urls.append({
            "loc": f"{base_url}/download_page?category_id={category.c_id}",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
        })

    # Documents
    documents = Document.query.all()
    for document in documents:
        dynamic_urls.append({
            "loc": f"{base_url}/get_document?document_id={document.id}",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
        })
    
    # Combine static and dynamic URLs
    urls = static_urls + dynamic_urls
    
    # Generate XML sitemap
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {"".join([f"<url><loc>{url['loc']}</loc><lastmod>{url['lastmod']}</lastmod></url>" for url in urls])}
    </urlset>
    """
    
    return Response(sitemap_xml, content_type="application/xml")
@app.route('/robots.txt')
def robots_txt():
    content = """User-agent: *
Allow: /
Disallow: /admin
Disallow: /login
Disallow: /logout
Sitemap: {base_url}/sitemap.xml
""".format(base_url=request.url_root.rstrip('/'))
    return Response(content, content_type='text/plain')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database Created Successfully")
        if not User.query.filter_by(username='tm').first():
            new_user = User(username=os.getenv('ADMIN_USERNAME'), password = generate_password_hash(os.getenv('ADMIN_PASSWORD')))
            db.session.add(new_user)
            db.session.commit()
    app.run(debug=True,host="0.0.0.0")
