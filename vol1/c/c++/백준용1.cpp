#include<iostream>

void copy(int (&_list1)[3], int (&_list2)[3])
{
    for(int i = 0; i < 3; ++i)
    {
        _list1[i] = _list2[i];
    }
}

int max(int a, int b, int c)
{
    if(a > b && a > c)
    {return a;}
    else if(b > a && b > c)
    {return b;}
    else
    {return c;}
}

int main()
{
    int n; int m1[3] = {0}; int m2[3] = {0}; int ram[3]; int inp;
    std::cin >> n;
    std::cin >> inp;
    m2[1] = inp;
    for(int i = 0; i < n - 1; ++i)
    {
        for(int j = 0; j < 3; ++j)
        {
            std::cout << m2[j] << " ";
        }
        std::cout << std::endl;
        std::cin >> inp;
        copy(ram, m2);
        m2[0] = max(m1[0], m1[1], m1[2]);
        m2[1] = ram[0] + inp;
        m2[2] = ram[1] + inp;
        copy(m1, ram);
    }
    std::cout << max(m2[0], m2[1], m2[2]);
    return 0;
}