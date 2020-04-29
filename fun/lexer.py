import re
from fun.exception import DecodeException, LexerException

rules = [
	('AT', ['@']),
	('SWAP', ['<=>']),
	('DETECT', ['<\?=']), #loop
	('TRANS', ['=>']),
	('REDUCE', ['>>']),
	('FILTER', ['\|']),
	('CALL', ['->']),
	('RETURN', ['<-']),
	('RELOAD', ['<<']),
	('UNFOLD', ['\.\.']),
	('OPERATOR', [r'[\+\*\-\/\^%!\?]', r'<=|>=|==|!=|<|>', r'(or)|(and)|(xor)', '#']),
	('STRING', [r'"(\\"|[^"])*"', r"'(\\'|[^'])*'"]),
	('NUMBER', [r'\d+\.\d+', r'\d+']),
	('NAME', [r'[a-zA-Z_]\w*']),
	('LPAREN', [r'\(']),
	('RPAREN', [r'\)']),
	('LBRACK', [r'\[']),
	('RBRACK', [r'\]']),
	('LCBRACK', ['{']),
	('RCBRACK', ['}']),
	('IGNORE', [r'[ \t\n]+']),
	('COLON', [':']),
	('COMMA', [',']),
	('SEMICOLON', [';']),
	('ASSIGN', ['=']),
]

rules = [(name, '|'.join(['({})'.format(p) for p in patterns])) for name, patterns in rules]
_regex = re.compile('|'.join(['(?P<{}>{})'.format(name, patterns) for name, patterns in rules]))
keywords = ['index', 'yes', 'no', 'nothing', 'always']

escape_regex = re.compile(r'\\(r|n|t|\\|\'|\")')
chars = {
	'r': '\r',
	'n': '\n',
	't': '\t',
	'\\': '\\',
	'"': '"',
	"'": "'",
}
def replace(matches):
	char = matches.group(1)[0]
	if char not in chars:
		raise DecodeException(char)
	return chars[char]
decode = lambda s: escape_regex.sub(replace, s[1:-1])

class Token:
	def __init__(self, name, value, line_no):
		self.name = name
		self.value = value
		self.line_no = line_no

def _tokenize(code, line_no):
	pos = 0
	while pos < len(code):
		matches = _regex.match(code, pos)
		if matches is not None:
			name = matches.lastgroup
			pos = matches.end(name)
			value = matches.group(name)
			if name in ('IGNORE', 'STRING'):
				line_no += value.count('\n')
			if name == 'IGNORE':
				continue
			if name == 'NAME' and value in keywords:
				yield Token(value.upper(), None, line_no)
			elif name == 'STRING':
				try:
					yield Token(name, decode(value), line_no)
				except DecodeException as e:
					raise LexerException('未知字符 {}'.format(e.info), line_no)
			else:
				yield Token(name, value, line_no)
		else:
			raise LexerException('非法字符 {}'.format(code[pos]), line_no)

class Tokens:
	def __init__(self, tokens):
		last_line = tokens[-1].line_no if tokens else 0
		self.tokens = tokens + [Token('EOF', None, last_line)]
		self._pos = 0
	@property
	def current(self):
		return self.tokens[self._pos]
	def consume(self, *name):
		current = self.current
		self._pos += 1
		if current.name in name:
			return current
		else:
			expected_name = ' 或 '.join(name)
			raise LexerException('希望得到一个{0} token，却得到{1} token。'.format(expected_name, current.name), current.line_no)
	def is_end(self):
		return self._pos == len(self.tokens)
	@classmethod
	def tokenize(cls, code, start_line=0):
		return cls(list(_tokenize(code, start_line)))
