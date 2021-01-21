#include<iostream>
#include<vector>
int main()
{
    int N;
    std::vector<int> num_list, stack, return_list;
    std::cin >> N;
    for(int i = 0; i < N; ++i)
    {
        int tmp;
        std::cin >> tmp;
        num_list.push_back(tmp);
    }
    stack.push_back(num_list.back());
    num_list.pop_back();
    return_list.push_back(-1);
    while(!num_list.empty())
    {
        int tmp = num_list.back();
        num_list.pop_back();
        if(tmp >= stack[0])
        {
            stack.clear();
            stack.push_back(tmp);
            return_list.push_back(-1);
        }
        else
        {
            int l = stack.size();
            while(true)
            {
                if(stack.back() > tmp)
                {
                    return_list.push_back(stack.back());
                    stack.push_back(tmp);
                    break;
                }
                else
                {stack.pop_back();}
            }
        }
    }
    for(int i = 0; i < N; ++i)
    {
        std::cout << return_list[N - 1 - i] << " ";
    }
}