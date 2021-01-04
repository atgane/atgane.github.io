#include<iostream>
int max(int _list[1001], int boundary)
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
    int memo_list[1001] = {0}; int n;
    std::cin >> n;
    for(int i = 0; i < n; ++i)
    {
        int temp_val;
        std::cin >> temp_val;
        if(i == 0)
        {
            memo_list[temp_val] += 1;
        }
        else
        {
            memo_list[temp_val] = max(memo_list, temp_val) + 1;
        }
    }
    std::cout << max(memo_list, 1001);
}
