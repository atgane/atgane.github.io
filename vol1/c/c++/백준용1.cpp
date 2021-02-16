#include<iostream>
#include<vector>

void del_parent(std::vector<int>& _root, std::vector<int>& _parent, int c_name)
{
    _parent[c_name] = 0;
    _root[c_name] = c_name;
}

int find_root(std::vector<int>& _root, std::vector<int>& _parent, int c_name)
{
    if(_root[c_name] != c_name)
    {_root[c_name] = find_root(_root, _parent, _parent[c_name]);}
    return _root[c_name];
}

int main()
{
    int N, Q;
    std::cin >> N;
    std::cin >> Q;
    std::vector<int> root(0, N + 1);
    std::vector<int> parent(0, N + 1);
    root[1] = 1;
    
    for(int i = 2; i < N + 1; ++i)
    {
        std::cin >> parent[i];
    }
    for(int i = 0; i < N + Q  - 1; ++i)
    {
        int flag;
        std::cin >> flag;
        if(flag == 0)
        {
            int tmp;
            std::cin >> tmp;
            del_parent(root, parent, tmp);
        }
        else
        {
            int tmp1, tmp2, name1, name2;
            std::cin >> tmp1 >> tmp2;
            name1 = find_root(root, parent, tmp1);
            name2 = find_root(root, parent, tmp2);
            if(name1 == name2)
            {std::cout << "YES\n";}
            else
            {std::cout << "NO\n";}
        }
    }
}