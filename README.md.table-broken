# CSS tools: check, refactor, minify

Author: Ryan Flynn
Copyright 2011 Ryan Flynn parseerror@gmail.com
MIT licensed: http://www.opensource.org/licenses/mit-license.php

### Goal:
An intuitive CSS toolkit that allows people to work on nicely
formatted CSS, then automatically refactor and minify for
publication. It stays out of your way, Does The Right Thing
and Just Works.

### Get Started!
    $ sudo apt-get install python-dev python-setuptools
    $ sudo easy_install simpleparse
    $ git clone git@github.com:rflynn/css-tools.git
    $ cd css-tools
    $ make test

Utilities:
* css-format
* css-refactor
* css-check

Bugs: https://github.com/rflynn/css-tools/issues

### Examples:

Here's a real-world example; before we have 2 box classes that are nearly
identical. `css-refactor --aggressive` finds the overlap and only declares
those attributes once.

|before			    	|after (aggressive)			|
|.oddBoxOut {		    	|.oddBoxOut, .evenBoxOut {		|
|  width: 12em;		    	|	padding: 0.5em;			|
|  float: left;		    	|	border: solid 1px black;	|
|  padding: 0.5em;	    	|	margin: 0.5em;			|
|  margin: 0.5em;		|	width: 12em;			|
|  border: solid 1px black;	|}					|
|}				|.evenBoxOut {				|
|    				|	float: right;			|
|.evenBoxOut {			|}					|
|  width: 12em;			|.oddBoxOut {				|
|  float: right;		|		float: left;		|
|  padding: 0.5em;		|}					|
|  margin: 0.5em;		|					|
|  border: solid 1px black;	|					|
|}				|					|


css-format --minify strips whitespaces, colons, etc. and reduces colors and other values to their shortest possible representation
`$ echo 'a { font-size: 10px; line-height: 1.2em; color: Yellow; }' \
 | ./css-refactor.py | ./css-format.py --minify`
a{color:#ff0;font:10px/1.2em}

