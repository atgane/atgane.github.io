#include<iostream>
#include<vector>
#include<stack>
int main()
{
    int N;
    std::stack<int> stack;
    std::vector<bool> result;
    std::cin >> N;
    std::vector<bool> data(N + 1, 1);
    stack.push(0);

    for(int i = 0; i < N; ++i)
    {
        int tmp;
        std::cin >> tmp;
        if(tmp > stack.top())
        {
            int j;
            if(stack.size() == 1)
            {j = 1;}
            else
            {j = stack.top();}
            while(j <= tmp)
            {
                if(data[j] == 1)
                {
                    data[j] = 0;
                    stack.push(j);
                    result.push_back(1);
                }
                j += 1;
            }
            stack.pop();
            result.push_back(0);
        }
        else if(tmp == stack.top())
        {
            stack.pop();
            result.push_back(0);
        }
        else
        {
            std::cout << "NO";
            return 0;
        }
    }
    for(int i = 0; i < result.size(); ++i)
    {
        if(result[i] == 1)
        {std::cout << "+\n";}
        else
        {std::cout << "-\n";}
    }
}