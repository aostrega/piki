Piki
====

Piki is a personal wiki website designed to be as comfortable, intuitive and elegant as possible. The client code is written in CoffeeScript with jQuery and rangy, and the server is written in Python with Flask and Elixir. It is released under the MIT license.

What makes it notable from a technical standpoint is that it uses a [heavily scripted web page](https://github.com/Skofo/Piki/blob/master/static/js/wiki.coffee) as an unobtrusive editor.

The live version is hosted here: [http://piki.heroku.com/](http://piki.heroku.com/)

Prerequisites
-------------
*  CoffeeScript
*  Python 2.5+
*  Pip

Instructions
------------
1.  Compile the .coffee files in static/js. (coffee -c static/js)
2.  Install the server dependencies. (pip install -r requirements.txt)
3.  Run the server. (python piki.py)