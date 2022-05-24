```c++
#include<iostream>
#include<cmath>
#include<time.h>
using namespace std;
void F1(double x) //函直接算法 
{
	double sum=0;
    for (int i=1; i<=100; i++)
        sum += pow(x,i)/i;   
    cout<<"F1="<<sum<<endl;  
}
void F2(double x) //秦九昭算法 
{
    double sum=0;
    for (int i=100; i>0; i--)
        sum = 1.0/i+sum*x;
    sum=sum*x;
    cout<<"F2="<<sum<<endl; 
}
int main()
{
	clock_t start,end;//数据类型是clock_t，需要头文件#include<time.h>
	double x=1.5;

	start=clock();
	F1(x);
	end=clock();
	cout<<"F1运行时间"<<(double)(end-start)/CLOCKS_PER_SEC<<endl;

	start=clock();
	F2(x);
	end=clock();
	cout<<"F2运行时间"<<(double)(end-start)/CLOCKS_PER_SEC<<endl;
	return 0;
}

```
