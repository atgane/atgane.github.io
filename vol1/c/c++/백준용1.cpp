#include<iostream>
int max(int _list[501], int boundary)
{
    int ret = 0;
    for(int i = 0; i < boundary; ++i)
    {
        if(ret < _list[i])
        {ret = _list[i];}
    }
    return ret;
}

int main()
{
    int memo_list[501] = {0}; int n;
    std::cin >> n;
    for(int i = 0; i < n; ++i)
    {
        int a, b;
        std::cin >> a;
        std::cin >> b;
        memo_list[a] = b;
    }
    int ret_list[501] = {0};
    int index = 0;
    for(int i = 0; i < 501; ++i)
    {
        if(memo_list[i] != 0)
        {
            if(index == 0)
            {
                ret_list[memo_list[i]] +=1;
                index +=1;
            }
            else
            {
                ret_list[memo_list[i]] = max(ret_list, memo_list[i]) + 1;
            }
        }
    }
    std::cout << n - max(ret_list, 501);
}
