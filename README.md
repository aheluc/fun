# Fun
Fun是一个**基于Python的脚本语言**。

擅长处理数据流，其高度的随意性和动态性可以使其代码精简而灵活。

## 特点(Feature)

### 自动lambda化(auto lambda)
当一个表达式中的存在变量未定义时，则整个表达式变为lambda表达式。

`fun = x * y;`
实质上等价于
```
fun = {
    <- x * y;
};
```

### 定义函数不需要声明参数列表(function statement without a parameter list)
*就像这样：*
```
fun = {
    x = arg;
    <- x;
};
```
只需要在调用时，给够所需的参数
`["arg": 5] -> fun;`

### 表是list与dict的融合(table is the only data structure which conbines list and dict)
你可以这样定义一个表：`table = [1, 2, 3, "word": "hi!"];`

### 生成器可以展开为表(a generator can unfold into a table)
你也可以这样定义一个表：`table = [..range << [0, 5]];`

### 函数可以在另一个函数内展开(function unfolding)
```
fun = {
    x = x + 1;
    x -> print;
};
another_fun = {
    x = 1;
    ..fun;
};
```
以此定义的another_fun实际上等价于
```
another_fun = {
    x = 1;
    x = x + 1;
    x -> print;
};
```

## 使用(Usage)

使用Fun不需要任何Python的第三方库。

你可以在[Fun 在线执行](http://sdbotwechat.zicp.io/fun_online)上尝试执行Fun。
