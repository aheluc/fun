from fun.utils import ParserScope, StackEvent
from fun.exception import ParserException
import fun.ast as ast

def number(tokens, _):
	token = tokens.consume('NUMBER')
	val = token.value
	try:
		val = int(val)
	except ValueError:
		val = float(val)
	return ast.Number(token.line_no, val)

def nothing(tokens, _):
	token = tokens.consume('NOTHING')
	return ast.Nothing(token.line_no)

def name(tokens, _):
	token = tokens.consume('NAME')
	id = token.value
	return ast.Identifier(token.line_no, id)

def bool_(tokens, _):
	token = tokens.consume('YES', 'NO')
	if token.name == 'YES':
		return ast.Bool(token.line_no, True)
	else:
		return ast.Bool(token.line_no, False)

def group(tokens, precedences):
	token = tokens.consume('LPAREN')
	right = expression(tokens, precedences.get(token.value, 0))
	tokens.consume('RPAREN')
	return ast.Group(token.line_no, right)

def variable(tokens, precedences):
	token = tokens.consume('AT')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is not None:
		return ast.Variable(token.line_no, right)
	raise ParserException('{0} 右侧表达式缺失'.format(token.value), token.line_no)

def index(tokens, _):
	if ParserScope.get_node_with('loop'):
		token = tokens.consume('INDEX')
		return ast.Index(token.line_no)
	else:
		raise ParserException('在循环外使用index', tokens.current.line_no)

def string(tokens, _):
	token = tokens.consume('STRING')
	return ast.String(token.line_no, token.value)

def unary_operator(tokens, precedences):
	if tokens.current.value not in ('-', '!', '?', '#'):
		raise ParserException('未知或未实现操作符 {0}'.format(tokens.current.value), tokens.current.line_no)
	token = tokens.consume('OPERATOR')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is not None:
		return ast.UnaryOperator(token.line_no, token.value, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def detect(tokens, left, precedences):
	token = tokens.consume('DETECT')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is not None:
		return ast.Detect(token.line_no, left, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def transform(tokens, left, precedences):
	token = tokens.consume('TRANS')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is not None:
		return ast.Transform(token.line_no, left, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def filter(tokens, left, precedences):
	token = tokens.consume('FILTER')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is not None:
		return ast.Filter(token.line_no, left, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def reduce(tokens, left, precedences):
	token = tokens.consume('REDUCE')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is not None:
		return ast.Reduce(token.line_no, left, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def binary_operator(tokens, left, precedences):
	if tokens.current.value not in ('+', '-', '*', '/', '^', '%', '>', '>=', '<', '<=', '==', '!=', 'and', 'or'):
		raise ParserException('未知或未实现操作符 {0}'.format(tokens.current.value), tokens.current.line_no)
	token = tokens.consume('OPERATOR')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is not None:
		return ast.BinaryOperator(token.line_no, token.value, left, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def subscript(tokens, left, precedences):
	token = tokens.consume('LBRACK')
	if tokens.current.name == 'ALWAYS':
		token = tokens.consume('ALWAYS')
		right = ast.Always(token.line_no)
	else:
		# 优先级永远低于括号内的
		right = expression(tokens)
	tokens.consume('RBRACK')
	if right is None:
		raise ParserException('下标不能为空', token.line_no)
	return ast.Subscript(token.line_no, left, right)

def reload(tokens, left, precedences):
	token = tokens.consume('RELOAD')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is None:
		raise ParserException('重装符 {0} 右侧表达式缺失'.format(token.value), token.line_no)
	return ast.Reload(token.line_no, left, right)

def fun(tokens, precedences):
	token = tokens.consume('LCBRACK')
	with ParserScope(StackEvent('fun', token)):
		body = statements(tokens, 'fun')
	tokens.consume('RCBRACK')
	return ast.FunStatementNode(token.line_no, body)

# exp | exp: exp | ALWAYS exp 
# 优先级永远低于括号内的
def table(tokens, precedences):
	start_token = tokens.consume('LBRACK')
	items = []
	while not tokens.is_end():
		if tokens.current.name == 'ALWAYS':
			token = tokens.consume('ALWAYS')
			tokens.consume('COLON')
			item = expression(tokens)
			if item is None:
				raise ParserException('映射右侧值表达式缺失'.format(tokens.current.value), tokens.current.line_no)
			items.append(ast.AlwaysItem(token.line_no, item))
		elif tokens.current.name == 'UNFOLD':
			tokens.consume('UNFOLD')
			right = expression(tokens)
			if right is not None:
				items.append(ast.Unfold(right.line_no, right))
			else:
				raise ParserException('展开操作符 {0} 右侧表达式缺失'.format(tokens.current.value), tokens.current.line_no)
		else:
			left = expression(tokens)
			if left is None:
				break
			if tokens.current.name == 'COLON':
				token = tokens.consume('COLON')
				right = expression(tokens)
				if right is None:
					raise ParserException('映射右侧值表达式缺失', left.line_no)
				items.append(ast.DictItem(token.line_no, left, right))
			else:
				items.append(ast.ListItem(left.line_no, left))
		if tokens.current.name == 'COMMA':
			tokens.consume('COMMA')
		else:
			break
	tokens.consume('RBRACK')
	return ast.TableStatementNode(start_token.line_no, items)

def incorrect_always(tokens, _):
	raise ParserException('always只能用于Table声明或下标', tokens.current.line_no)

def call(tokens, left, precedences):
	token = tokens.consume('CALL')
	right = expression(tokens, precedences.get(token.value, 0))
	if right is None:
		raise ParserException('右侧调用函数 {0} 缺失'.format(token.value), token.line_no)
	return ast.Call(token.line_no, left, right)

def get_next_precedence(tokens):
	if tokens.current:
		parser, precedences = infix.get(tokens.current.name, (None, None))
		if parser:
			return precedences.get(tokens.current.value, 0)
	return 0

def expression(tokens, precedence=0):
	prefix_parser, precedences = prefix.get(tokens.current.name, (None, None))
	if prefix_parser:
		left = prefix_parser(tokens, precedences)
		if left:
			while precedence < get_next_precedence(tokens):
				infix_parser, precedences = infix.get(tokens.current.name, (None, None))
				op = infix_parser(tokens, left, precedences)
				if op:
					left = op
			return left
	return None

infix = {
	#'REPLACE': (replace, {}),
	'LBRACK': (subscript, {
		'[': 14,
	}),
	'CALL': (call, {
		'->': 1,
	}),
	'DETECT': (detect, {
		'<?=': 2,
	}),
	'TRANS': (transform, {
		'=>': 2,
	}),
	'FILTER': (filter, {
		'|': 2,
	}),
	'REDUCE': (reduce, {
		'>>': 2,
	}),
	'RELOAD': (reload, {
		'<<': 15,
	}),
	'OPERATOR': (binary_operator, {
		'^': 11,
		
		'*': 10,
		'/': 10,
		'%': 10,
		
		'+': 9,
		'-': 9,
		
		'>': 8,
		'>=': 8,
		'<': 8,
		'<=': 8,
		
		'==': 7,
		'!=': 7,
		
		'and': 6,
		
		'or': 5,
	}),
}

prefix = {
	'NUMBER': (number, {}),
	'NOTHING': (nothing, {}),
	'INDEX': (index, {}), #用Scope传递
	'NAME': (name, {}),
	'YES': (bool_, {}),
	'NO': (bool_, {}),
	'STRING': (string, {}),
	'LPAREN': (group, {}),
	'ALWAYS': (incorrect_always, {}),
	'AT': (variable, {
		'@': 14,
	}),
	'OPERATOR': (unary_operator, {
		'-': 12,
		'!': 12,
		'?': 12,
		'#': 12,
	}),
	'LCBRACK': (fun, {}),
	'LBRACK': (table, {}),
}

def call_block_statement(tokens):
	token = tokens.consume('CALL')
	right = expression(tokens)
	tokens.consume('SEMICOLON')
	if right is not None:
		return ast.CallBlock(token.line_no, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def unfold_statement(tokens):
	'''展开语句'''
	token = tokens.consume('UNFOLD')
	right = expression(tokens)
	tokens.consume('SEMICOLON')
	if right is not None:
		return ast.Unfold(token.line_no, right)
	raise ParserException('操作符 {0} 右侧表达式缺失'.format(token.value), token.line_no)

def assignment_statement(tokens, left):
	'''赋值语句'''
	line_no = tokens.current.line_no
	if isinstance(left, ast.Readonly):
		raise ParserException('不可将值赋予只读的关键词', tokens.current.line_no)
	tokens.consume('ASSIGN')
	right = expression(tokens)
	tokens.consume('SEMICOLON')
	if right is not None:
		return ast.Assignment(line_no, left, right)
	raise ParserException('赋值语句右侧表达式缺失', token.line_no)

def swap_statement(tokens, left):
	'''交换语句'''
	line_no = tokens.current.line_no
	tokens.consume('SWAP')
	right = expression(tokens)
	if isinstance(left, ast.Readonly) or isinstance(right, ast.Readonly):
		raise ParserException('不可将值赋予只读的关键词', tokens.current.line_no)
	tokens.consume('SEMICOLON')
	if right is not None:
		return ast.Swap(line_no, left, right)
	raise ParserException('交换语句右侧表达式缺失', token.line_no)

def expression_statement(tokens):
	exp = expression(tokens)
	if exp:
		if tokens.current.name == 'ASSIGN':
			return assignment_statement(tokens, exp)
		elif tokens.current.name == 'SWAP':
			return swap_statement(tokens, exp)
		else:
			tokens.consume('SEMICOLON')
			return exp

def return_statement(tokens):
	'''返回语句'''
	if ParserScope.get_node_with('fun'):
		token = tokens.consume('RETURN')
		right = expression(tokens)
		if right is None:
			right = ast.Nothing(tokens.current.line_no)
		tokens.consume('SEMICOLON')
		return ast.Return(tokens.current.line_no, right)
	else:
		raise ParserException('在函数外使用return', tokens.current.line_no)

statement = {
	'CALL': [
		call_block_statement,
		('fun', 'program'),
	],
	'RETURN': [
		return_statement, 
		('fun',),
	],
	'UNFOLD': [
		unfold_statement, 
		('fun',),
	],
}

def statements(tokens, scope):
	stmts = []
	while not tokens.is_end():
		parser, container = statement.get(tokens.current.name, [expression_statement, ('fun', 'program')])
		if scope not in container:
			raise ParserException('{} 不能在 {} 中使用'.format(tokens.current.name, scope), tokens.current.line_no)
		stmt = parser(tokens)
		if stmt:
			stmts.append(stmt)
		else:
			break
	return stmts

def program(tokens):
	line_no = tokens.current.line_no
	stmts = statements(tokens, 'program')
	if tokens.consume('EOF'):
		return ast.Program(line_no, stmts)
