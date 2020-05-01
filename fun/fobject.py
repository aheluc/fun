from fun.utils import InterpreterScope, StackEvent, recursion_forbidden, MAX_LOOP_COUNT
from fun.exception import ReturnMessage, StopMessage, RuntimeException

intent = '    '

class FinalValue:
	def _type(self):
		return type(self).__name__
	def eval(self, env):
		pass
	@classmethod
	def _key2fun(cls, py_val):
		types = {
			int: Number,
			str: String,
		}
		fun_type = types.get(type(py_val))
		if fun_type:
			return fun_type(py_val)
		else:
			return py_val
	def _str(self):
		return self._code()
	def _add(self, right, pattern):
		if pattern == (FinalValue, String):
			return String._py2fun(self._str() + right.value._str())
	def _copy(self):
		return self
	def _eq(self, right, pattern):
		return Bool._py2fun(self._id() == right.value._id())
	def _ne(self, right, pattern):
		return Bool._py2fun(self._id() != right.value._id())
	def _and(self, right, pattern):
		return Bool._py2fun(self._bool().py_val and right._bool().py_val)
	def _or(self, right, pattern):
		return Bool._py2fun(self._bool().py_val or right._bool().py_val)
	def _xor(self, right, pattern):
		return Bool._py2fun(self._bool().py_val != right._bool().py_val)

class Const(FinalValue):
	def _id(self):
		return self.py_val
	@classmethod
	def _py2fun(cls, py_val):
		return cls(py_val)

class Obj(FinalValue):
	def _id(self):
		return self
	def _copy(self):
		raise Exception()

class Nothing(Const):
	def __init__(self):
		self.py_val = Nothing
		self.value = self
	def _code(self,scope=0):
		return 'nothing'
	def _copy(self):
		return self
	def _bool(self):
		return fobject_no

class Bool(Const):
	def __init__(self, py_val):
		self.py_val = py_val
		self.value = self
	def _code(self, scope=0):
		return 'yes' if self.py_val else 'no'
	def _id(self):
		return self
	@classmethod
	def _py2fun(self, py_val):
		return fobject_yes if py_val else fobject_no
	def _bool(self):
		return self
	def _not(self):
		return Bool._py2fun(not self.py_val)
	def _and(self, right, pattern):
		return Bool._py2fun(self.py_val and right._bool().py_val)
	def _or(self, right, pattern):
		return Bool._py2fun(self.py_val or right._bool().py_val)
	def _xor(self, right, pattern):
		return Bool._py2fun(self.py_val != right._bool().py_val)

fobject_yes = Bool(True)
fobject_no = Bool(False)
fobject_nothing = Nothing()

class Number(Const):
	def __init__(self, py_val):
		self.py_val = py_val
		self.value = self
	def _code(self, scope=0):
		return str(self.py_val)
	def _bool(self):
		return Bool._py2fun(self.py_val)
	def _not(self):
		return Bool._py2fun(not self.py_val)
	def _neg(self):
		return Number(-self.py_val)
	def _add(self, right, pattern):
		if pattern == (Number, Number):
			return Number._py2fun(self.py_val + right.value.py_val)
		else:
			return String._py2fun(self._str() + right.value._str())
	def _sub(self, right, pattern):
		return Number._py2fun(self.py_val - right.value.py_val)
	def _mul(self, right, pattern):
		if pattern == (Number, Number):
			return Number._py2fun(self.py_val * right.value.py_val)
		else:
			return String._py2fun(self.py_val * right.value.py_val)
	def _div(self, right, pattern):
		return Number._py2fun(self.py_val / right.value.py_val)
	def _mod(self, right, pattern):
		return Number._py2fun(self.py_val % right.value.py_val)
	def _pow(self, right, pattern):
		return Number._py2fun(self.py_val ** right.value.py_val)
	def _gt(self, right, pattern):
		return Bool._py2fun(self.py_val > right.value.py_val)
	def _ge(self, right, pattern):
		return Bool._py2fun(self.py_val >= right.value.py_val)
	def _lt(self, right, pattern):
		return Bool._py2fun(self.py_val < right.value.py_val)
	def _le(self, right, pattern):
		return Bool._py2fun(self.py_val <= right.value.py_val)

class String(Const):
	def __init__(self, py_val):
		self.py_val = py_val
		self.value = self
	def _str(self):
		return self.py_val
	def _code(self, scope=0):
		return '"{}"'.format(self.py_val)
	def _bool(self):
		return Bool._py2fun(self.py_val)
	def _add(self, right, pattern):
		return String._py2fun(self._str() + right.value._str())
	def _mul(self, right, pattern):
		return String._py2fun(self.py_val * right.value.py_val)

class Fun(Obj):
	def __init__(self, body):
		self.body = body
		self.value = self
	def _bool(self):
		return Bool._py2fun(self.body)
	def _len(self):
		return Number(len(self.body))
	def _code(self, scope=0):
		body = [stmt._code(scope + 1) for stmt in self.body]
		inner_intent = intent * (scope + 1)
		outer_intent = intent * scope
		body = ';\n'.join(['{intent}{stmt}'.format(intent=inner_intent, stmt=stmt) for stmt in body])
		body = body + ';' if body else ''
		return '{' + '\n{body}\n{intent}'.format(intent=outer_intent, body=body) + '}'
	def _copy(self):
		return Fun([stmt._copy() for stmt in self.body])
	def _reload(self, initializer, pattern=None):
		return Generator([stmt._copy() for stmt in self.body], initializer.value._copy())
	def _init(self, args=None):
		if args is not None:
			return Table()._reload(args)
		return Table()
	def _call(self, line_no, env):
		for stmt in self.body:
			stmt.eval(env)
	def make_args(self, args):
		if isinstance(args, Table):
			return args
		else:
			container = Table()
			container._list.append(args)
			return container

class Generator(Fun):
	def __init__(self, body, initializer):
		self.body = body
		self.initializer = initializer
		self.start_step = 0
		self.eof = False
		self.value = self
	def _copy(self):
		return Generator([stmt._copy() for stmt in self.body], self.initializer._copy())
	def _init(self, args=None):
		if args is not None:
			self.initializer = self.initializer._reload(args)
		return self.initializer
	def _reload(self, initializer, pattern=None):
		return Generator([stmt._copy() for stmt in self.body], initializer.value._copy())
	def _map(self, right, pattern=None):
		return Transform(self._copy(), right.value._copy())
	def _filter(self, right, pattern=None):
		return Filter(self._copy(), right.value._copy())
	def _reduce(self, line_no, right, env, pattern=None):
		if self.eof:
			raise StopMessage()
		count = 0
		reducer = right.value
		reduced = fobject_nothing
		while True:
			count += 1
			if count > MAX_LOOP_COUNT:
				raise RuntimeException(line_no, '你可能陷入了死循环')
			left_env = Environment(self._init(), parent=env)
			try:
				self._call(line_no, left_env)
			except ReturnMessage as ret:
				value = ret.value
			except StopMessage:
				self.eof = True
				raise ReturnMessage(reduced)
			args = self.make_args(value)
			right_env = Environment(reducer._init(args), parent=env)
			try:
				reducer._call(line_no, right_env)
			except ReturnMessage as reducer_ret:
				reduced = reducer_ret.value
			except StopMessage:
				pass
	@recursion_forbidden('call_generator', '生成器不可以递归调用')
	def _call(self, line_no, env):
		if self.eof:
			raise StopMessage()
		count = 0
		while True:
			count += 1
			if count > MAX_LOOP_COUNT:
				raise RuntimeException(line_no, '你可能陷入了死循环')
			try:
				for step in range(self.start_step, len(self.body)):
					self.body[step].eval(env)
				# 如果不是从头执行，则可以多执行一次(restart if it is not the first time to be called)
				if self.start_step > 0:
					for step, stmt in enumerate(self.body):
						stmt.eval(env)
				self.eof = True
				raise StopMessage()
			except ReturnMessage as msg:
				self.start_step = step + 1
				raise msg

class Transform(Generator):
	def __init__(self, producter, transformer, initializer=None):
		self.producter = producter
		self.transformer = transformer
		self.initializer = initializer if initializer is not None else Table()
		self.eof = False
	def _bool(self):
		return fobject_yes
	def _len(self):
		return Number(self.producter._len().py_val + self.transformer._len().py_val)
	def _reload(self, initializer, pattern=None):
		return Transform(self.producter._copy(), self.transformer._copy(), initializer.value._copy())
	def _init(self, args=None):
		if args is not None:
			self.initializer = self.initializer._reload(args)
		return self.initializer
	@recursion_forbidden('call_generator', '生成器不可以递归调用')
	def _call(self, line_no, env):
		if self.eof:
			raise StopMessage()
		left_env = Environment(self.producter._init(), parent=env)
		try:
			self.producter._call(line_no, left_env)
		except ReturnMessage as ret:
			value = ret.value
		except StopMessage:
			self.eof = True
			raise StopMessage()
		if isinstance(self.transformer, Fun):
			args = self.make_args(value)
			right_env = Environment(self.transformer._init(args), parent=env)
			try:
				self.transformer._call(line_no, right_env)
			except ReturnMessage as ret:
				raise ret
			except StopMessage:
				pass
			raise RuntimeException(line_no, '变换函数没有返回值')
		elif isinstance(self.transformer, Table):
			raise ReturnMessage(self.transformer._getitem(line_no, value))
	def _copy(self):
		return Transform(self.producter._copy(), self.transformer._copy(), self.initializer._copy())
	def _code(self, scope=0):
		return '{} => {}'.format(self.producter._code(scope), self.transformer._code(scope))

class Filter(Generator):
	def __init__(self, producter, checker, initializer=None):
		self.producter = producter
		self.checker = checker
		self.initializer = initializer if initializer is not None else Table()
		self.eof = False
	def _bool(self):
		return fobject_yes
	def _len(self):
		return Number(self.producter._len().py_val + self.checker._len().py_val)
	def _reload(self, initializer, pattern=None):
		return Filter(self.producter._copy(), self.checker._copy(), initializer.value._copy())
	def _init(self, args=None):
		if args is not None:
			self.initializer = self.initializer._reload(args)
		return self.initializer
	@recursion_forbidden('call_generator', '生成器不可以递归调用')
	def _call(self, line_no, env):
		if self.eof:
			raise StopMessage()
		count = 0
		while True:
			count += 1
			if count > MAX_LOOP_COUNT:
				raise RuntimeException(line_no, '你可能陷入了死循环')
			left_env = Environment(self.producter._init(), parent=env)
			try:
				self.producter._call(line_no, left_env)
			except ReturnMessage as ret:
				value = ret.value
			except StopMessage:
				self.eof = True
				raise StopMessage()
			if isinstance(self.checker, Fun):
				args = self.make_args(value)
				right_env = Environment(self.checker._init(args), parent=env)
				try:
					self.checker._call(line_no, right_env)
				except ReturnMessage as checker_ret:
					if checker_ret.value._bool().py_val:
						raise ReturnMessage(value)
				except StopMessage:
					pass
			elif isinstance(self.checker, Table):
				if self.checker._getitem(line_no, value)._bool().py_val:
					raise ReturnMessage(value)
	def _copy(self):
		return Filter(self.producter._copy(), self.checker._copy(), self.initializer._copy())
	def _code(self, scope=0):
		return '{} | {}'.format(self.producter._code(scope), self.checker._code(scope))

class Always(Obj): pass

class Table(Obj):
	def __init__(self):
		self.type = 'Table'
		self._list = []
		self._dict = {}
		self.always = None
		self.value = self
	def eval(self, env):
		pass
	def _bool(self):
		return Bool._py2fun(self._list or self._dict or self.always is not None)
	def _len(self):
		return Number(len(self._list) + len(self._dict))
	def _reload(self, right, pattern=None):
		new = Table()
		if len(self._list) <= len(right.value._list):
			new._list = right.value._list[:]
		else:
			new._list = right.value._list + self._list[len(right.value._list):]
		new._dict = {**self._dict, **right.value._dict}
		if right.value.always is not None:
			new.always = right.value.always
		else:
			new.always = self.always
		return new
	def _setitem(self, key, value):
		'''key不能是value，而要是node(因为包含了字面信息，如行号)'''
		if not isinstance(key.value, Always):
			_key = key.value._id()
			if isinstance(_key, int) and 0 <= _key < len(self._list):
				self._list[_key] = value
			else:
				self._dict[_key] = value
		else:
			self.always = value
	def _getitem(self, line_no, key, default=None):
		'''key不能是value，而要是node(因为包含了字面信息，如行号)'''
		if not isinstance(key.value, Always):
			_key = key.value._id()
			if isinstance(_key, int) and 0 <= _key < len(self._list):
				return self._list[_key]
			else:
				value = self._dict.get(_key, self.always)
				if value is None:
					if default is None:
						raise RuntimeException(line_no, '不存在的key值 {}'.format(key._code()))
					else:
						return default
				else:
					return value
		else:
			if self.always is None:
				raise RuntimeException(line_no, 'always未定义')
			return self.always
	def _code(self, scope=0):
		events = InterpreterScope.get_stack()
		# 防止循环引用时，无限生成代码
		if [event for event in events if event.name == 'table_code' and event.info == self]:
			return '[...]'
		with InterpreterScope(StackEvent('table_code', self)):
			def key_code(key, scope):
				if isinstance(key, FinalValue):
					return key._code(scope)
				else:
					return str(key)
			items = [item._code(scope + 1) for item in self._list]
			items += ['{}: {}'.format(key_code(key, scope + 1), value._code(scope + 1)) for key, value in self._dict.items()]
			if self.always is not None:
				items.append('always: {}'.format(self.always._code(scope + 1)))
			inner_intent = intent * (scope + 1)
			outer_intent = intent * scope
			items = ',\n'.join(['{intent}{item}'.format(intent=inner_intent, item=item) for item in items])
			return '[\n{items}\n{intent}]'.format(intent=outer_intent, items=items)
	def _copy(self):
		new = Table()
		new._list = [*self._list]
		new._dict = {**self._dict}
		new.always = self.always
		return new

class Undefined:
	@classmethod
	def _code(cls):
		return 'undefined'

class Environment:
	def __init__(self, initializer, parent=None, temporary=False):
		self.user_data = initializer
		self.system_data = {}
		self.parent = parent
		self.temporary = temporary
	def set(self, key, val):
		if self.temporary and self.parent is not None:
			self.parent.set(key, val)
		else:
			self.user_data._setitem(key, val)
	def get(self, line_no, key):
		val = self.user_data._getitem(line_no, key, Undefined)
		if val == Undefined and self.parent is not None:
			val = self.parent.get(line_no, key)
		return val
	def sys_set(self, key, val):
		self.system_data[key] = val
	def sys_get(self, key):
		val = self.system_data.get(key, Undefined)
		if val == Undefined and self.parent is not None:
			val = self.parent.sys_get(key)
		return val
