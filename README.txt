
CSS tools: analyze, refactor, minify

Planned css-tools:
	css-format
		css-format --minify
	css-refactor
	css-check
		css-check --validate=css2
		css-check --non-standard
		css-check --cross-browser

Dependencies:
	sudo easy_install simpleparse
	if that breaks, install the python headers:
		sudo apt-get install python-dev
		sudo yum install python-dev

Examples:

# original string is 113 chars + newline
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 10px} body{margin:10px} table{margin:10px}' | wc -c
114

# css-refactor will merge child properties into parents and merge selectors with identical blocks into one
# css-format pretty-prints CSS by default
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 10px} body{margin:10px} table{margin:10px}' | ./css-refactor.py | ./css-format.py
body, table {
        margin: 10px;
}
div {
        font-family: Arial;
        margin: 10px;
}
span {
        font: 10px Arial;
}

# css-refactor --aggressive will merge shared subsets of declaration blocks, as long as it will save space. see how div's margin:10px was merged into the first block
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 10px} body{margin:10px} table{margin:10px}' | ./css-refactor.py --aggressive | ./css-format.py
body, table, div {
        margin: 10px;
}
div {
        font-family: Arial;
}
span {
        font: 10px Arial;
}

# css-format --minify strips unnecessary whitespace, semi-colons, quotes and other characters where possible
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 10px} body{margin:10px} table{margin:10px}' | ./css-refactor.py --aggressive | ./css-format.py --minify
body,table,div{margin:10px}div{font-family:Arial}span{font:10px Arial}

# aggressively refactored and minified string is 70 chars + newline
$ echo 'span{font-size:10px; font-family:Arial} div{font-family:Arial; margin: 10px} body{margin:10px} table{margin:10px}' | ./css-refactor.py --aggressive | ./css-format.py --minify | wc -c
71

