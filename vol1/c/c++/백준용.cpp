#include<iostream>

int mul(int _A, int _B, int _C)
{
    if(_B == 1)
    {return _A % C;}
    else if(_B % 2 == 0)
    {
        return mul(_A, _B / 2, _C) * mul(_A, _B / 2, _C) % _C;
    }
    else
    {
        return mul(_A, _B / 2, _C) * mul(_A, _B / 2, _C) * 2 % _C;
    }
}

int main()
{
    int A, B, C;
    std::cin >> A >> B >> C;
    std::cout << mul(A, B, C);
}