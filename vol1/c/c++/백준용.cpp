#include<deque>
#include<iostream>

int main()
{
    int n, flag = 1;
    std::deque<int> deq;
    std::cin >> n;
    for(int i = 1; i <= n; ++i)
    {
        deq.push_back(i);
    }
    while(deq.size() != 1)
    {
        if(flag % 2 == 1)
        {
            deq.pop_front();
        }
        else
        {
            int tmp = deq.front();
            deq.push_back(tmp);
            deq.pop_front();
        }   
        flag += 1;
    }
    std::cout << deq.front();
}