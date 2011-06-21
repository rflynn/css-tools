
CSS tools: check, refactor, minify

Author: Ryan Flynn
Copyright 2011 Ryan Flynn <parseerror@gmail.com>
MIT licensed: http://www.opensource.org/licenses/mit-license.php

Goal:
	An intuitive CSS toolkit that allows people to work on nicely
	formatted CSS, then automatically refactor and minify for
	publication. It stays out of your way, Does The Right Thing
	and Just Works.

Interface:
	css-format
		css-format --minify
	css-refactor
		css-refactor --aggressive
	css-check

Install:
	sudo easy_install simpleparse
	if that breaks, install the python headers:
		sudo apt-get install python-dev
		sudo yum install python-dev
	git clone git@github.com:rflynn/css-tools.git
	cd css-tools/src

Bugs: https://github.com/rflynn/css-tools/issues

Example:

# css-refactor will merge child properties such as 'font-size' and 'line-height' into parent property 'font'
$ echo 'a { font-size: 10px; line-height: 1.2em; color: Yellow; }' | ./css-refactor.py
a {
        color: Yellow;
        font: 10px/1.2em;
}

# css-format --minify strips whitespaces, colons, etc. and reduces colors and other values to their shortest possible representation
$ echo 'a { font-size: 10px; line-height: 1.2em; color: Yellow; }' | ./css-refactor.py | ./css-format.py --minify
a{color:#ff0;font:10px/1.2em}

# a more complex example involving declarations that share some members
# original string length
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 5px} body{margin:5px} table{margin:5px}' | wc -c
111

# css-refactor merges child properties into parents and selectors with identical blocks into one
# css-format pretty-prints by default
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 5px} body{margin:5px} table{margin:5px}' | ./css-refactor.py | ./css-format.py
body, table {
        margin: 5px;
}
div {
        font-family: Arial;
        margin: 5px;
}
span {
        font: 10px Arial;
}

# css-refactor --aggressive will merge shared subsets of declaration blocks when it saves space to do so.
# div's margin:5px was merged into the first block
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 5px} body{margin:5px} table{margin:5px}' | ./css-refactor.py --aggressive | ./css-format.py
body, table, div {
        margin: 5px;
}
div {
        font-family: Arial;
}
span {
        font: 10px Arial;
}

# css-format --minify strips unnecessary whitespace, semi-colons, quotes and other characters where possible
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 5px} body{margin:5px} table{margin:5px}' | ./css-refactor.py --aggressive | ./css-format.py --minify
body,table,div{margin:5px}div{font-family:Arial}span{font:10px Arial}

# aggressively refactored and minified string
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 5px} body{margin:5px} table{margin:5px}' | ./css-refactor.py --aggressive | ./css-format.py --minify | wc -c
70

