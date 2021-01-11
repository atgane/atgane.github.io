#include<iostream>
void change(bool (&_a)[52][52], int _x, int _y)
{
    for(int i = _y; i < _y + 3; ++i)
    {
        for(int j = _x; j < _x + 3; ++j)
        {
            _a[i][j] = !_a[i][j];
        }
    }
}
void prt(bool a[52][52], int n, int m)
{
    for(int i = 0; i < n; ++i)
    {
        for(int j = 0; j < m; ++j)
        {
            std::cout << a[i][j];
        }
        std::cout << std::endl;
    }
    std::cout << std::endl;
}
bool eq(bool _a[52][52], bool _b[52][52], int n, int m)
{
    bool ret = 1;
    for(int i = 0; i < n; ++i)
    {
        for(int j = 0; j < m; ++j)
        {
            if(_a[i][j] != _b[i][j])
            {
                std::cout << i << " " << j << " " << std::endl;
                ret = 0;
                break;
            }
        }
        if(ret == 0)
        {
            break;
        }
    }
    return ret;
}

int main()
{
    int n, m;
    bool a[52][52], b[52][52];
    std::cin >> n;
    std::cin >> m;
    for(int i = 0; i < n; ++i)
    {
        char c[50];
        std::cin >> c;
        for(int j = 0; j < m; ++j)
        {
            a[i][j] = int(c[j]) - 48;
        }
    }
    for(int i = 0; i < n; ++i)
    {
        char c[50];
        std::cin >> c;
        for(int j = 0; j < m; ++j)
        {
            b[i][j] = int(c[j]) - 48;
        }
    }
    for(int i = 0; i < n; ++i)
    {
        for(int j = 0; j < m; ++j)
        {
            b[i][j] = a[i][j] ^ b[i][j];
            a[i][j] = 0;
        }
    }
    prt(a, n, m);
    prt(b, n, m);
    int cnt = 0;
    for(int i = 0; i < n - 2; ++i)
    {
        for(int j = 0; j < m - 2; ++j)
        {
            if(a[i][j] != b[i][j])
            {
                cnt += 1;
                change(a, j, i);
                prt(a, n, m);
            }
        }
    }
    bool flag = eq(a, b, n, m);
    std::cout << flag << std::endl;
    prt(a, n, m);
    prt(b, n, m);
    if(flag)
    {std::cout << cnt;}
    else
    {std::cout << -1;}
}