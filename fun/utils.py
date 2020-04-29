from fun.exception import RuntimeException

class Scope:
	stack = {}
	@classmethod
	def get_stack(cls):
		return Scope.stack.get(cls, [])
	@classmethod
	def get_node_with(cls, target):
		stack = Scope.stack.get(cls, [])
		if stack:
			stack = [event for event in stack if target == event.name]
			if stack:
				return stack[-1]
		return None
	@classmethod
	def clear_all(cls):
		Scope.stack.clear()
	@classmethod
	def clear(cls):
		if cls in Scope.stack:
			Scope.stack[cls].clear()
	def __init__(self, info=None):
		self.info = info
	def __enter__(self):
		if type(self) not in Scope.stack:
			Scope.stack[type(self)] = []
		Scope.stack[type(self)].append(self.info)
	def __exit__(self, exc_type, exc_val, exc_tb):
		Scope.stack[type(self)].pop()

class LexerScope(Scope): pass
class ParserScope(Scope): pass
class InterpreterScope(Scope): pass

class StackEvent:
	def __init__(self, name, info):
		self.name = name
		self.info = info

def recursion_forbidden(event_name, err_msg):
	def wrapper(func):
		def inner(self, line_no, env):
			event_stack = InterpreterScope.get_stack()
			if [event for event in event_stack if event.name == event_name and event.info == self]:
				raise RuntimeException(line_no, err_msg)
			with InterpreterScope(StackEvent(event_name, self)):
				func(self, line_no, env)
		return inner
	return wrapper

MAX_LOOP_COUNT = 900
