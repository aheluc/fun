import fun.ast as ast
import fun.fobject as obj
from fun.exception import ReturnMessage, StopMessage, RuntimeException

class Builtin(obj.Fun):
	def _init(self, args=None):
		if args is not None:
			return obj.Table()._reload(args)
		return obj.Table()
	def _reload(self, initializer, pattern=None):
		return obj.Generator([], initializer.value._copy())
	def _len(self):
		return Number(1)

class Print(Builtin):
	def __init__(self, out):
		self.out = out
		self.value = self
	def _bool(self):
		return obj.Bool._py2fun(True)
	def _code(self, scope=0):
		return '{**builtin: print**}'
	def _call(self, line_no, env):
		self.out.append(' '.join([item._code() for item in env.user_data._list]))
	
class Stop(Builtin):
	def __init__(self):
		self.value = self
	def _bool(self):
		return obj.Bool._py2fun(True)
	def _code(self, scope=0):
		return '{**builtin: stop**}'
	def _call(self, line_no, env):
		arg = env.get(line_no, obj.Number(0))
		if arg != obj.Undefined and arg.value._bool().py_val:
			raise StopMessage()

class NumberGenerator(obj.Generator):
	def __init__(self, initializer):
		self.initializer = initializer
		self.eof = False
		self.value = self
	def _copy(self):
		return NumberGenerator(self.initializer.value._copy())
	def _bool(self):
		return obj.Bool._py2fun(True)
	def _code(self, scope=0):
		return '{**builtin: number generator**}'
	def _init(self, args=None):
		if args is not None:
			self.initializer = self.initializer._reload(args)
		return self.initializer
	def _reload(self, initializer, pattern=None):
		return NumberGenerator(initializer.value._copy())
	def _map(self, right, pattern=None):
		return obj.Transform(self._copy(), right.value._copy())
	def _filter(self, right, pattern=None):
		return obj.Filter(self._copy(), right.value._copy())
	def _call(self, line_no, env):
		if self.eof:
			raise StopMessage()
		start, end = self.initializer._getitem(line_no, obj.Number(0)), self.initializer._getitem(line_no, obj.Number(1))
		if start.py_val > end.py_val:
			self.eof = True
			raise StopMessage()
		ret = ReturnMessage(start._copy())
		self.initializer._setitem(obj.Number(0), start._add(obj.Number(1), (obj.Number, obj.Number)))
		raise ret

class Range(Builtin):
	def __init__(self):
		self.value = self
	def _bool(self):
		return obj.Bool._py2fun(True)
	def _code(self, scope=0):
		return '{**builtin: range**}'
	def _reload(self, initializer, pattern=None):
		return NumberGenerator(initializer.value._copy())
	def _call(self, line_no, env):
		raise ReturnMessage(NumberGenerator(initializer.value._copy()))

class TableIter(obj.Generator):
	def __init__(self, initializer):
		self.initializer = initializer
		self.cursor = 0
		self._dict_to_visit = list(self.initializer._dict.keys())
		self._dict_cursor = 0
		self.eof = False
		self.value = self
	def _copy(self):
		return TableIter(self.initializer.value._copy())
	def _bool(self):
		return obj.Bool._py2fun(True)
	def _code(self, scope=0):
		return '{**builtin: table iter**}'
	def _init(self, args=None):
		if args is not None:
			self.initializer = self.initializer._reload(args)
		return self.initializer
	def _reload(self, initializer, pattern=None):
		return TableIter(initializer.value._copy())
	def _map(self, right, pattern=None):
		return obj.Transform(self._copy(), right.value._copy())
	def _filter(self, right, pattern=None):
		return obj.Filter(self._copy(), right.value._copy())
	def _call(self, line_no, env):
		if self.eof:
			raise StopMessage()
		if self.cursor < len(self.initializer._list):
			return_value = obj.Table()
			return_value._list.append(obj.Number(self.cursor))
			return_value._list.append(self.initializer._list[self.cursor])
			ret = ReturnMessage(return_value)
			self.cursor += 1
			raise ret
		elif self._dict_cursor < len(self._dict_to_visit):
			return_value = obj.Table()
			return_value._list.append(obj.FinalValue._key2fun(self._dict_to_visit[self._dict_cursor]))
			return_value._list.append(self.initializer._dict[self._dict_to_visit[self._dict_cursor]])
			ret = ReturnMessage(return_value)
			self._dict_cursor += 1
			raise ret
		else:
			self.eof = True
			raise StopMessage()

class Iter(Builtin):
	def __init__(self):
		self.value = self
	def _bool(self):
		return obj.Bool._py2fun(True)
	def _code(self, scope=0):
		return '{**builtin: iter**}'
	def _call(self, line_no, env):
		if not env.user_data._list:
			raise RuntimeException(line_no, 'iter至少需要一个参数')
		if not isinstance(env.user_data._list[0], obj.Table):
			raise RuntimeException(line_no, 'iter需要一个table作为参数')
		raise ReturnMessage(TableIter(env.user_data._list[0]._copy()))
