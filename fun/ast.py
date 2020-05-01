import abc
from fun.utils import InterpreterScope, StackEvent, recursion_forbidden, MAX_LOOP_COUNT
from fun.exception import ReturnMessage, StopMessage, RuntimeException
import fun.fobject as obj

intent = '    '
class Unsolved: pass

def is_unsolvable(*nodes):
	for node in nodes:
		if node.value == Unsolved:
			return node
	return None

def clear(*nodes):
	for node in nodes:
		if not isinstance(node, obj.FinalValue):
			node.value = Unsolved

def unable_to_eval(env, *nodes):
	clear(*nodes)
	for node in nodes:
		node.eval(env)
	return is_unsolvable(*nodes)

def innermost(node):
	while node.type == 'Group':
		node = node.inner
	return node

def auto_lambda(node):
	return obj.Fun([Return(node.line_no, node)])

class Readonly: pass

class Node():
	def __init__(self, line_no):
		self.line_no = line_no
		self.value = Unsolved
		self.type = type(self).__name__
		self.parent = None
		self.chilren = []
	def _type(self):
		return type(self).__name__
	def _code(self, scope):
		raise Exception('Not Implemented!') 
	def set_parent_for_children(self, *children):
		self.chilren = children
		for child in children:
			child.parent = self
	# 暂时废止
	def _currying(self, try_env):
		if self.type == 'Identifier':
			value = try_env.get(self.id)
			if value == obj.Undefined:
				return 1
			else:
				return 0
		elif not self.chilren:
			return 0
		else:
			return sum([child._currying(try_env) for child in self.children])

class Nothing(Node):
	def __init__(self, line_no):
		super(Nothing, self).__init__(line_no)
		self.val = Nothing
		self.value = self
	def eval(self, env):
		self.value = obj.fobject_nothing
	def _code(self,scope=0):
		return 'nothing'
	def _copy(self):
		return self
	def _bool(self):
		return Bool(self.line_no, False)

class Bool(Node):
	def __init__(self, line_no, val):
		super(Bool, self).__init__(line_no)
		self.val = val
	def eval(self, env):
		self.value = obj.Bool._py2fun(self.val)
	def _code(self, scope=0):
		if self.val:
			return 'yes'
		else:
			return 'no'
	def _copy(self):
		return Bool(self.line_no, self.val)

class Number(Node):
	def __init__(self, line_no, val):
		super(Number, self).__init__(line_no)
		self.val = val
	def eval(self, env):
		self.value = obj.Number(self.val)
	def _code(self, scope=0):
		return str(self.val)
	def _copy(self):
		return Number(self.line_no, self.val)

class String(Node):
	def __init__(self, line_no, val):
		super(String, self).__init__(line_no)
		self.val = val
	def eval(self, env):
		self.value = obj.String(self.val)
	def _code(self, scope=0):
		return '"{}"'.format(self.val)
	def _copy(self):
		return String(self.line_no, self.val)

class OperatorValidator:
	chinese_name = {
		'_neg': '取负',
		'_not': '取非',
		'_bool': '取真值',
		'_len': '取长度',
		'_add': '加法',
		'_sub': '减法',
		'_mul': '乘法',
		'_div': '除法',
		'_mod': '取余',
		'_pow': '幂',
		'_gt': '大于',
		'_ge': '大于等于',
		'_lt': '小于',
		'_le': '小于等于',
		'_eq': '等于',
		'_ne': '不等于',
		'_and': '与',
		'_or': '或',
		'_xor': '异或',
		'_map': '转换',
		'_filter': '过滤',
		'_reduce': '降维',
		'_reload': '重装',
	}
	def __init__(self, opt_name, validator):
		self.opt_name = opt_name
		self.validator = validator
	def validate(self, line_no, *operands):
		def _validate(rule, operands):
			for id, operand in enumerate(operands):
				if not isinstance(operand.value, rule[id]):
					return False
			return True
		for rule in self.validator:
			if _validate(rule, operands):
				return self.opt_name, rule
		operand_name = ', '.join(['{}: {}'.format(operand.value._type(), operand._code()) for operand in operands])
		raise RuntimeException(line_no, '不可对 ({}) 使用 {} 操作符'.format(operand_name, OperatorValidator.chinese_name[self.opt_name]))

class Index(Node, Readonly):
	def __init__(self, line_no):
		super(Index, self).__init__(line_no)
	def eval(self, env):
		value = obj.Number(env.sys_get(Index))
		if value == obj.Undefined:
			raise RuntimeException(self.line_no, '不可在循环外使用index')
		self.value = value
	def _code(self, scope=0):
		return '#{right}'.format(right=self.right._code(scope))
	def _copy(self):
		return Index(self.line_no)

class Variable(Node):
	def __init__(self, line_no, right):
		super(Variable, self).__init__(line_no)
		self.set_parent_for_children(right)
		self.right = right
	def eval(self, env):
		clear(self.right)
		self.right.eval(env)
		if not is_unsolvable(self.right):
			if not isinstance(self.right.value, (obj.Number, obj.String)):
				raise RuntimeException(self.right.line_no, '{} 不是整数或字符串'.format(self.right._code()))
			value = env.get(self.line_no, self.right.value)
			if value == obj.Undefined:
				event = InterpreterScope.get_node_with('auto_lambda')
				if event:
					if event.info.value == Unsolved:
						event.info.value = auto_lambda(event.info)
				else:
					raise RuntimeException(self.right.line_no, '未定义变量: @{}'.format(self.right._code()))
			else:
				self.value = value
	def _code(self, scope=0):
		return '@{right}'.format(right=self.right._code(scope))
	def _copy(self):
		return Variable(self.line_no, self.right._copy())

class BinaryOperator(Node):
	def __init__(self, line_no, opt, left, right):
		super(BinaryOperator, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.opt = opt
		self.left = left
		self.right = right
	def eval(self, env):
		binary_operator_validator = {
			'+': OperatorValidator('_add', 
				[
					(obj.Number, obj.Number),
					(obj.FinalValue, obj.String),
					(obj.String, obj.FinalValue)
				]),
			'-': OperatorValidator('_sub', 
				[(obj.Number, obj.Number)]),
			'*': OperatorValidator('_mul', 
				[
					(obj.Number, obj.Number),
					(obj.Number, obj.String),
					(obj.String, obj.Number)
				]),
			'/': OperatorValidator('_div', 
				[(obj.Number, obj.Number)]),
			'%': OperatorValidator('_mod', 
				[(obj.Number, obj.Number)]),
			'^': OperatorValidator('_pow', 
				[(obj.Number, obj.Number,)]),
			'>': OperatorValidator('_gt', 
				[(obj.Number, obj.Number)]),
			'>=': OperatorValidator('_ge', 
				[(obj.Number, obj.Number)]),
			'<': OperatorValidator('_lt', 
				[(obj.Number, obj.Number)]),
			'<=': OperatorValidator('_le', 
				[(obj.Number, obj.Number)]),
			'==': OperatorValidator('_eq', 
				[(obj.FinalValue, obj.FinalValue)]),
			'!=': OperatorValidator('_ne', 
				[(obj.FinalValue, obj.FinalValue)]),
			'and': OperatorValidator('_and', 
				[(obj.FinalValue, obj.FinalValue)]),
			'or': OperatorValidator('_or', 
				[(obj.FinalValue, obj.FinalValue)]),
			'xor': OperatorValidator('_xor', 
				[(obj.FinalValue, obj.FinalValue)]),
		}
		clear(self.left, self.right)
		self.left.eval(env)
		self.right.eval(env)
		if not is_unsolvable(self.left, self.right):
			validator = binary_operator_validator[self.opt]
			method_name, pattern = validator.validate(self.line_no, self.left, self.right)
			operator = getattr(self.left.value, method_name)
			self.value = operator(self.right, pattern)
	def _code(self, scope=0):
		return '{left} {opt} {right}'.format(left=self.left._code(scope), opt=self.opt, right=self.right._code(scope))
	def _copy(self):
		return BinaryOperator(self.line_no, self.opt, self.left._copy(), self.right._copy())

class UnaryOperator(Node):
	def __init__(self, line_no, opt, right):
		super(UnaryOperator, self).__init__(line_no)
		self.set_parent_for_children(right)
		self.opt = opt
		self.right = right
	def eval(self, env):
		method_name = {
			'-': '_neg',
			'!': '_not',
			'?': '_bool',
			'#': '_len',
		}
		clear(self.right)
		self.right.eval(env)
		if not is_unsolvable(self.right):
			try:
				operation = getattr(self.right.value, method_name[self.opt])
				self.value = operation()
			except AttributeError:
				raise RuntimeException(self.right.line_no, '{0} 无法进行 {1} 操作'.format(self.right._code(), OperatorValidator.chinese_name[method_name[self.opt]]))
	def _code(self, scope=0):
		return '({opt}{right})'.format(opt=self.opt, right=self.right._code(scope))
	def _copy(self):
		return UnaryOperator(self.line_no, self.opt, self.right._copy())		

class Group(Node):
	def __init__(self, line_no, inner):
		super(Group, self).__init__(line_no)
		self.set_parent_for_children(inner)
		self.inner = inner
	def eval(self, env):
		clear(self.inner)
		self.inner.eval(env)
		if not is_unsolvable(self.inner):
			self.value = self.inner.value
	def _code(self, scope=0):
		return '({})'.format(self.inner._code(scope))
	def _copy(self):
		return Group(self.line_no, self.inner._copy())

class Identifier(Node):
	def __init__(self, line_no, id):
		super(Identifier, self).__init__(line_no)
		self.id = id
	def eval(self, env):
		value = env.get(self.line_no, obj.String(self.id))
		if value == obj.Undefined:
			event = InterpreterScope.get_node_with('auto_lambda')
			if event:
				if event.info.value == Unsolved:
					event.info.value = auto_lambda(event.info)
			else:
				raise RuntimeException(self.line_no, '未定义变量: {}'.format(self.id))
		else:
			self.value = value
	def _code(self, scope=0):
		return str(self.id)
	def _copy(self):
		return Identifier(self.line_no, self.id)

class Program(Node):
	def __init__(self, line_no, stmts):
		super(Program, self).__init__(line_no)
		self.set_parent_for_children(*stmts)
		self.stmts = stmts
	def eval(self, env):
		for stmt in self.stmts:
			stmt.eval(env)
	def _copy(self):
		new_body = [stmt._copy() for stmt in self.stmts]
		return Program(new_body)
	def _code(self, scope=0):
		return '\n'.join([stmt._code(scope) for stmt in self.stmts])

class Trigger(Node): pass

class CallBlock(Trigger):
	def __init__(self, line_no, right):
		super(CallBlock, self).__init__(line_no)
		self.set_parent_for_children(right)
		self.right = right
	def eval(self, env):
		clear(self.right)
		self.right.eval(env)
		if is_unsolvable(self.right):
			return
		if not isinstance(self.right.value, obj.Fun):
			raise RuntimeException(self.line_no, '{} 不可被调用'.format(self.right._code()))
		callable = self.right.value
		call_env = obj.Environment(callable._init(), parent=env, temporary=True)
		callable._call(self.line_no, call_env)
	def _copy(self):
		return CallBlock(self.line_no, self.right._copy())
	def _code(self, scope=0):
		return '-> {}'.format(self.right._code(scope))

class Call(Trigger):
	def __init__(self, line_no, left, right):
		super(Call, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.left = left
		self.right = right
	def eval(self, env):
		clear(self.left, self.right)
		self.left.eval(env)
		with InterpreterScope(StackEvent('auto_lambda', self.right)):
			self.right.eval(env)
		if is_unsolvable(self.left, self.right):
			return
		args, callable = self.left.value, self.right.value
		args = callable.make_args(args)
		if not isinstance(callable, obj.Fun):
			raise RuntimeException(self.line_no, '{} 不可被调用'.format(self.right._code()))
		call_env = obj.Environment(callable._init(args), parent=env)
		try:
			callable._call(self.line_no, call_env)
		except ReturnMessage as ret:
			self.value = ret.value
		else:
			self.value = Nothing(self.line_no)
	def _copy(self):
		return Call(self.line_no, self.left._copy(), self.right._copy())
	def _code(self, scope=0):
		return '{} -> {}'.format(self.left._code(scope), self.right._code(scope))

class Detect(Trigger):
	def __init__(self, line_no, left, right):
		super(Detect, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.left = left
		self.right = right
	def eval(self, env):
		clear(self, self.left, self.right)
		self.left.eval(env)
		with InterpreterScope(StackEvent('auto_lambda', self.right)):
			self.right.eval(env)
		if is_unsolvable(self.left, self.right):
			return
		generator, detector = self.left.value, self.right.value
		if not isinstance(generator, obj.Generator):
			raise RuntimeException(self.line_no, '只有Generator才可以被检测，而 {} 不是Generator'.format(self.left._code()))
		if not isinstance(detector, obj.Fun):
			raise RuntimeException(self.line_no, '{} 不可作为检测器'.format(right._code()))
		gen_env = obj.Environment(generator._init(None), parent=env)
		count = 0
		while True:
			gen_env.sys_set(Index, count)
			if count > MAX_LOOP_COUNT:
				raise RuntimeException(self.line_no, '你可能陷入了死循环')
			try:
				generator._call(self.line_no, gen_env)
			except ReturnMessage as ret:
				value = ret.value
			except StopMessage:
				break
			args = detector.make_args(value)
			detector_env = obj.Environment(detector._init(args), parent=env)
			detector_env.sys_set(Index, count)
			try:
				detector._call(self.line_no, detector_env)
			except ReturnMessage as ret:
				if ret.value._bool().val:
					self.value = ret.value
					return
			count += 1
		self.value = Nothing(self.line_no)
	def _copy(self):
		return Detect(self.line_no, self.left._copy(), self.right._copy())
	def _code(self, scope=0):
		return '{} <?= {}'.format(self.left._code(scope), self.right._code(scope))

class Transform(Node):
	def __init__(self, line_no, left, right):
		super(Transform, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.left = left
		self.right = right
	def eval(self, env):
		validator = OperatorValidator('_map', 
			[
				(obj.Generator, obj.Fun),
				(obj.Generator, obj.Table),
				# to do
				#(obj.Table, obj.Fun),
				#(obj.Table, obj.Table),
			]
		)
		clear(self, self.left, self.right)
		self.left.eval(env)
		with InterpreterScope(StackEvent('auto_lambda', self.right)):
			self.right.eval(env)
		if is_unsolvable(self.left, self.right):
			return
		opt_name, pattern = validator.validate(self.line_no, self.left, self.right)
		map_method = getattr(self.left.value, opt_name)
		self.value = map_method(self.right, pattern)
	def _copy(self):
		return Transform(self.line_no, self.left._copy(), self.right._copy())
	def _code(self, scope=0):
		return '{} => {}'.format(self.left._code(scope), self.right._code(scope))

class Filter(Node):
	def __init__(self, line_no, left, right):
		super(Filter, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.left = left
		self.right = right
	def eval(self, env):
		validator = OperatorValidator('_filter', 
			[
				(obj.Generator, obj.Fun),
				(obj.Generator, obj.Table),
				# to do
				#(obj.Table, obj.Fun),
				#(obj.Table, obj.Table),
			]
		)
		clear(self, self.left, self.right)
		self.left.eval(env)
		with InterpreterScope(StackEvent('auto_lambda', self.right)):
			self.right.eval(env)
		if is_unsolvable(self.left, self.right):
			return
		opt_name, pattern = validator.validate(self.line_no, self.left, self.right)
		filter_method = getattr(self.left.value, opt_name)
		self.value = filter_method(self.right, pattern)
	def _copy(self):
		return Filter(self.line_no, self.left._copy(), self.right._copy())
	def _code(self, scope=0):
		return '{} | {}'.format(self.left._code(scope), self.right._code(scope))

class Reduce(Node):
	def __init__(self, line_no, left, right):
		super(Reduce, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.left = left
		self.right = right
	def eval(self, env):
		validator = OperatorValidator('_reduce', 
			[
				(obj.Generator, obj.Generator),
			]
		)
		clear(self, self.left, self.right)
		self.left.eval(env)
		with InterpreterScope(StackEvent('auto_lambda', self.right)):
			self.right.eval(env)
		if is_unsolvable(self.left, self.right):
			return
		opt_name, pattern = validator.validate(self.line_no, self.left, self.right)
		reduce_method = getattr(self.left.value, opt_name)
		try:
			self.value = reduce_method(self.line_no, self.right, env, pattern)
		except ReturnMessage as ret:
			self.value = ret.value
		else:
			self.value = Nothing(self.line_no)
	def _copy(self):
		return Filter(self.line_no, self.left._copy(), self.right._copy())
	def _code(self, scope=0):
		return '{} >>| {}'.format(self.left._code(scope), self.right._code(scope))

class Unfold(Node):
	def __init__(self, line_no, right):
		super(Unfold, self).__init__(line_no)
		self.set_parent_for_children(right)
		self.right = right
	def eval(self, env):
		clear(self.right)
		self.right.eval(env)
		if is_unsolvable(self.right):
			return
		if isinstance(self.right.value, obj.Table):
			if self.parent.type == 'TableStatementNode':
				table = InterpreterScope.get_node_with('table_statement').info
				table._list += self.right.value._list
				table._dict = {**table._dict, **self.right.value._dict}
				if self.right.value.always is not None:
					table.always = self.right.value.always
			else:
				raise RuntimeException(self.line_no, '不可以在表声明之外展开表')
		elif isinstance(self.right.value, obj.Fun):
			if self.parent.type == 'FunStatementNode':
				outer_body = InterpreterScope.get_node_with('fun_statement').info
				outer_body += self.right.value.body
			elif self.parent.type == 'TableStatementNode':
				if not isinstance(self.right.value, obj.Generator):
					raise RuntimeException(self.line_no, '只有生成器才可以在表声明内展开')
				table = InterpreterScope.get_node_with('table_statement').info
				generator = self.right.value
				gen_env = obj.Environment(generator._init(), parent=env)
				count = 0
				while True:
					gen_env.sys_set(Index, count)
					if count > MAX_LOOP_COUNT:
						raise RuntimeException(self.line_no, '你可能陷入了死循环')
					try:
						generator._call(self.line_no, gen_env)
					except ReturnMessage as ret:
						value = ret.value
					except StopMessage:
						break
					if isinstance(value, obj.Table):
						table._list += value._list
						table._dict = {**table._dict, **value._dict}
						table.always = value.always if value.always is not None else table.always
					else:
						table._list.append(value)
					count += 1
			else:
				raise RuntimeException(self.line_no, '不可以在函数声明和表声明之外展函数')
		else:
			raise RuntimeException(self.line_no, '{} 不可以进行展开操作'.format(self.right._code()))
	def _code(self, scope=0):
		return '..{}'.format(self.right._code(scope))
	def _copy(self):
		return Unfold(self.line_no, self.right._copy())

class Reload(Node):
	def __init__(self, line_no, left, initializer):
		super(Reload, self).__init__(line_no)
		self.set_parent_for_children(left, initializer)
		self.left = left
		self.initializer = initializer
	def eval(self, env):
		validator = OperatorValidator('_reload', 
			[
				(obj.Fun, obj.Table),
				(obj.Table, obj.Table),
			]
		)
		clear(self.left, self.initializer)
		with InterpreterScope(StackEvent('auto_lambda', self.left)):
			self.left.eval(env)
		self.initializer.eval(env)
		if not is_unsolvable(self.left, self.initializer):
			opt_name, pattern = validator.validate(self.line_no, self.left, self.initializer)
			reload_method = getattr(self.left.value, opt_name)
			self.value = reload_method(self.initializer, pattern)
	def _copy(self):
		return Reload(self.line_no, self.left._copy(), self.initializer._copy())
	def _code(self, scope=0):
		return '{} << {}'.format(self.left._code(scope), self.initializer._code(scope))

class FunStatementNode(Node):
	def __init__(self, line_no, body):
		super(FunStatementNode, self).__init__(line_no)
		self.set_parent_for_children(*body)
		self.body = body
	def eval(self, env):
		body = []
		with InterpreterScope(StackEvent('fun_statement', body)):
			for stmt in self.body:
				if stmt.type == 'Unfold':
					stmt.eval(env)
				else:
					body.append(stmt)
		self.value = obj.Fun(body)
	def _code(self, scope=0):
		body = [stmt._code(scope + 1) for stmt in self.body]
		inner_intent = intent * (scope + 1)
		outer_intent = intent * scope
		body = ';\n'.join(['{intent}{stmt}'.format(intent=inner_intent, stmt=stmt) for stmt in body])
		body = body + ';' if body else ''
		return '{' + '\n{body}\n{intent}'.format(intent=outer_intent, body=body) + '}'
	def _copy(self):
		body = [stmt._copy() for stmt in self.body]
		return FunStatementNode(self.line_no, body)

class Subscript(Node):
	def __init__(self, line_no, collection, key):
		super(Subscript, self).__init__(line_no)
		self.set_parent_for_children(collection, key)
		self.collection = collection
		self.key = key
	def eval(self, env):
		clear(self.collection, self.key)
		self.collection.eval(env)
		self.key.eval(env)
		if not is_unsolvable(self.collection, self.key):
			try:
				self.value = self.collection.value._getitem(self.line_no, self.key)
			except AttributeError:
				raise RuntimeException(self.collection.line_no, '{}不是容器'.format(self.collection._code()))
	def _code(self, scope=0):
		return '{collection}[{key}]'.format(collection=self.collection._code(scope), key=self.key._code(scope))
	def _copy(self):
		collection = self.collection._copy()
		key = self.key._copy()
		return Subscript(self.line_no, collection, key)

class Assignment(Node):
	def __init__(self, line_no, left, right):
		super(Assignment, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.left = left
		self.right = right
	def eval(self, env):
		node = innermost(self.left)
		def setitem(left, right, env):
			clear(left.collection, left.key, right)
			left.collection.eval(env)
			left.key.eval(env)
			with InterpreterScope(StackEvent('auto_lambda', right)):
				right.eval(env)
			if not is_unsolvable(left.collection, left.key, right):
				collection, key = left.collection.value, left.key
				try:
					collection._setitem(key, right.value)
				except AttributeError:
					raise RuntimeException(left.collection.line_no, '{}不是容器'.format(left.collection._code()))
				self.value = right.value
		
		def assignment(left, right, env):
			clear(left, right)
			with InterpreterScope(StackEvent('auto_lambda', right)):
				right.eval(env)
			if not is_unsolvable(right):
				env.set(obj.String(left.id), right.value)
			self.value = right.value

		evaluators = {
			'Subscript': setitem,
			'Identifier': assignment,
		}
		evaluate = evaluators.get(node.type, None)
		if evaluate:
			evaluate(node, self.right, env)
		else:
			raise RuntimeException(node.line_no, '不可以向{}赋值'.format(node._code()))
	def _code(self, scope=0):
		return '{left} = {right}'.format(left=self.left._code(scope), right=self.right._code(scope))
	def _copy(self):
		left = self.left._copy()
		right = self.right._copy()
		return Assignment(self.line_no, left, right)

class Return(Node):
	def __init__(self, line_no, right):
		super(Return, self).__init__(line_no)
		self.set_parent_for_children(right)
		self.right = right if right else Nothing()
	def eval(self, env):
		clear(self.right)
		with InterpreterScope(StackEvent('auto_lambda', self.right)):
			self.right.eval(env)
		if not is_unsolvable(self.right):
			msg = ReturnMessage(self.right.value)
			raise msg
	def _code(self, scope=0):
		return '<- {right}'.format(right=self.right._code(scope))
	def _copy(self):
		return Return(self.line_no, self.right._copy())

class ListItem(Node):
	def __init__(self, line_no, item):
		super(ListItem, self).__init__(line_no)
		self.set_parent_for_children(item)
		self.item = item
	def eval(self, env):
		table = InterpreterScope.get_node_with('table_statement').info
		clear(self.item)
		with InterpreterScope(StackEvent('auto_lambda', self.item)):
			self.item.eval(env)
		if not is_unsolvable(self.item):
			table._list.append(self.item.value)
	def _code(self, scope=0):
		return self.item._code(scope)
	def _copy(self):
		return ListItem(self.line_no, self.item)

class DictItem(Node):
	def __init__(self, line_no, left, right):
		super(DictItem, self).__init__(line_no)
		self.set_parent_for_children(left, right)
		self.left = left
		self.right = right
	def eval(self, env):
		clear(self.left, self.right)
		self.left.eval(env)
		with InterpreterScope(StackEvent('auto_lambda', self.right)):
			self.right.eval(env)
		if not is_unsolvable(self.left, self.right):
			table = InterpreterScope.get_node_with('table_statement').info
			table._dict[self.left.value._id()] = self.right.value
	def _code(self, scope=0):
		return '{}: {}'.format(self.left._code(scope), self.right._code(scope))
	def _copy(self):
		return DictItem(self.line_no, self.left, self.right)

class AlwaysItem(Node):
	def __init__(self, line_no, item):
		super(AlwaysItem, self).__init__(line_no)
		self.set_parent_for_children(item)
		self.item = item
	def eval(self, env):
		clear(self.item)
		with InterpreterScope(StackEvent('auto_lambda', self.item)):
			self.item.eval(env)
		if not is_unsolvable(self.item):
			table = InterpreterScope.get_node_with('table_statement').info
			table.always = self.item.value
	def _code(self, scope=0):
		return 'always: {}'.format(self.item._code(scope))
	def _copy(self):
		return AlwaysItem(self.line_no, self.item)

class Always(Node, Readonly):
	def __init__(self, line_no):
		super(Always, self).__init__(line_no)
		#self.value = self
	def eval(self, env):
		if self.parent.type == 'Subscript' and self.parent.key == self:
			self.value = obj.Always()
		else:
			raise RuntimeException(self.line_no, 'always关键字除下标外不可用于他处')
	def _code(self, scope=0):
		return 'always'
	def _copy(self):
		return Always(self.line_no)

class TableStatementNode(Node):
	def __init__(self, line_no, items):
		super(TableStatementNode, self).__init__(line_no)
		self.set_parent_for_children(*items)
		self.items = items
	def eval(self, env):
		table = obj.Table()
		with InterpreterScope(StackEvent('table_statement', table)):
			for item in self.items:
				item.eval(env)
		self.value = table
	def _copy(self):
		return TableStatementNode(self.line_no, [item._copy() for item in self.items])
	def _code(self, scope=0):
		items = [item._code(scope + 1) for item in self.items]
		inner_intent = intent * (scope + 1)
		outer_intent = intent * scope
		items = ',\n'.join(['{intent}{item}'.format(intent=inner_intent, item=item) for item in items])
		return '[\n{items}\n{intent}]'.format(intent=outer_intent, items=items)

