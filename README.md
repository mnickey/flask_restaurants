# FLASK RESTAURANTS
This is a demonstration of how Flask can be used to create a simple app.  
The main technologies used in this project are python, flask, OAuth, SQLAlchemy, requests, url_for, redirect and database sessions.  
Creating this project provided a solid understanding of Flask and how easily it could be used in order to get a site up and running quickly.

_Areas that should be noticed are:_  
* the bootstrap styling
* the login button that changes to logout when a user is logged in & vice-versa
* The use of Facebook & Google+ login methods
* The Contact Us button that will send an email (to me) when the proper authorization is given
The authorization here is based on Goggles App Passwords, this allows the publication of a password based on a users application. I can verify that this works on MY system and will submit proof as needed.  

### CONFIGURATION & INSTALLATION INSTRUCTIONS  
#####To clone this project:  
* Clone this repository from https://github.com/mnickey/flask_restaurants.git  

#####Creating the database:  
1. Inside your vagrant shell, create the database by typing `python database_setup.py`.  
2. To populate the database with seed data, type `python lotsofmenus.py`.  

###OPERATING INSTRUCTIONS  
#####To run:  
1. CD to your vagrant shell  
2. Type in `vagrant up`  
3. Type in `vagrant ssh`  
4. CD to the menu_app directory  
5. Run the applicatin with `python finalproject.py`  
6. In your web-browser navigate to `http://localhost:5000/restaurants/` or `http://localhost:5000`.  

####FILE MANIFEST  
*finalproject.py* -- this is the main file that houses the logic of all the inner-workings. This file needs to be run to see the final result.  
*database_setup.py* -- this is the database setup file.   
*lotsofmenus.py* -- Once the database has been setup, this will populate seed data into the database and ready to display by `finalproject.py`.  
###CONTACT INFORMATION  
Feel free to contact me with any requests, questions or ideas at [mnickey@gmail.com](mailto:mnickey@gmail.com) .  
###KNOWN BUGS & TROUBLESHOOTING  
Please submit any bugs to the contact address above. I will address them as soon as I can.  
###CREDITS & ACKNOWLEDGEMENTS    
Special thanks goes to the team at Udacity for their constant professional help, my dog Anna for always knowing when it was time for a break, my lovely girlfriend, Rachelle, for letting me Rubber Duck this code with her.   
###PENDING FUTURE IMPROVEMENTS  
In no particular order, the future improvements that will be implemented and are currently being addressed are:  
- use of a login_required decorator -- the reason behind this is to reduce the amount of re-used code and make this DRY.  
- Give the user an option to login without having to use either Facebook ro Google+.  

###CHANGELOG  
For a changelog of all files, please view the history of this git repository.  

---  

###COPYRIGHT & LICENSING INFORMATION  
The MIT License (MIT)

Copyright (c) 2015 Michael Nickey

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.