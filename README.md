# flask_restaurants
This is a demonstration of how Flask can be used to create a simple app.
The main technologies used in this project are python, flask, OAuth, SQLAlchemy and requests.

Areas that should be noticed are:

* the bootstrap styling
* the login button that changes to logout when a user is logged in & vice-versa
* The use of Facebook & Google+ login methods
* The Contact Us button that will send an email (to me) when the proper authorization is given
The authorization here is based on Googles App Passwords, this allows the publication of a password based on a users
application. I can verify that this works on MY system and will submit proof as needed.

To clone this project:

* Clone this repository from https://github.com/mnickey/flask_restaurants.git

To use:

1. CD to your vagrant shell
2. Type in `vagrant up`
3. Type in `vagrant ssh`
4. CD to the menu_app directory
5. Run the applicatin with `python finalproject.py`
6. In your web-browser navigate to `http://localhost:5000/restaurants/`
