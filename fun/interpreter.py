import fun.lexer as lexer
import fun.parser as parser
import fun.ast as ast
import fun.fobject as obj
from fun.builtin import Print, Stop, Range, Iter
from fun.exception import CodeControlMessage, LexerException, ParserException, RuntimeException

def make_env(stdout):
	env = obj.Environment(obj.Table())
	env.user_data._dict['print'] = Print(stdout)
	env.user_data._dict['stop'] = Stop()
	env.user_data._dict['range'] = Range()
	env.user_data._dict['iter'] = Iter()
	return env

def repl():
	stdout = []
	env = make_env(stdout)
	while True:
		try:
			tokens = lexer.Tokens.tokenize(input('>>> '))
			parser.program(tokens).eval(env)
		except LexerException as e:
			stdout.append('line: {}, error: {}'.format(e.line_no, e.info))
		except ParserException as e:
			stdout.append('line: {}, error: {}'.format(e.line_no, e.info))
		except RuntimeException as e:
			stdout.append('line: {}, error: {}'.format(e.line_no, e.info))
		except CodeControlMessage as ret:
			stdout.append('不可在函数外使用返回或引发生成器终止')
		output = '\n'.join(stdout)
		if output:
			print(output)
		stdout.clear()

def repl_online(code):
	stdout = []
	env = make_env(stdout)
	try:
		tokens = lexer.Tokens.tokenize(code, start_line=1)
		parser.program(tokens).eval(env)
	except LexerException as e:
		stdout.append('line: {}, error: {}'.format(e.line_no, e.info))
	except ParserException as e:
		stdout.append('line: {}, error: {}'.format(e.line_no, e.info))
	except RuntimeException as e:
		stdout.append('line: {}, error: {}'.format(e.line_no, e.info))
	except CodeControlMessage as e:
		stdout.append('不可在函数外使用返回或引发生成器终止')
	return '\n'.join(stdout)

