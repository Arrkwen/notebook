## 接口的实现

1 结构体指针赋值给接口

2 结构体实现的方法只能比接口多，否则不是接口类型， 但是接口类型只能调用

```go
type Persist interface {
	Hello()
}

type A struct {
	name string
}

func (a *A) Hello() {
	fmt.Println(a.name)
}

func (a *A) NameA() {
	fmt.Println("A!")
}

type B struct {
	name string
}

func (b *B) Hello1() {
	fmt.Println(b.name)
}


type C struct {
	persist Persist
}

func PersistPrint(obj *C) {
	obj.persist.Hello()
}

func main() {
	a := &A{
		name: "xiao",
	}
	// b := &B{
	// 	name: "kun",
	// }
	// b不能赋值给C的perisist
	c := &C{
		persist: a,
	}
	PersistPrint(c)
}

```
