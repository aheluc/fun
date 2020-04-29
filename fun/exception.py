
class CodeControlMessage(Exception): pass

class ReturnMessage(CodeControlMessage):
	def __init__(self, value):
		self.value = value

class StopMessage(CodeControlMessage): pass

class DecodeException(Exception):
	def __init__(self, info):
		super(DecodeException, self).__init__()
		self.info = info

class RuntimeException(Exception):
	def __init__(self, line_no, info):
		super(RuntimeException, self).__init__()
		self.line_no = line_no
		self.info = info

class LexerException(Exception):
	def __init__(self, info, line_no):
		super(LexerException, self).__init__()
		self.info = info
		self.line_no = line_no

class ParserException(Exception):
	def __init__(self, info, line_no):
		super(Exception, self).__init__()
		self.info = info
		self.line_no = line_no
