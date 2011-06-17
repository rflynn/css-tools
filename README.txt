
CSS tools: check, refactor, minify

Author: Ryan Flynn
Copyright 2011 Ryan Flynn <parseerror@gmail.com>
MIT licensed: http://www.opensource.org/licenses/mit-license.php

Bugs: https://github.com/rflynn/css-tools/issues

Interface:
	css-format
		css-format --minify
	css-refactor
	css-check

Install:
	sudo easy_install simpleparse
	if that breaks, install the python headers:
		sudo apt-get install python-dev
		sudo yum install python-dev
	git clone git@github.com:rflynn/css-tools.git
	cd css-tools/src

Example:

$ echo 'a { font-size: 10px; line-height: 1.2em; color: Yellow; }' | ./css-refactor.py
a {
        color: Yellow;
        font: 10px/1.2em;
}

$ echo 'a { font-size: 10px; line-height: 1.2em; color: Yellow; }' | ./css-refactor.py | ./css-format.py --minify
a{color:#ff0;font:10px/1.2em}

