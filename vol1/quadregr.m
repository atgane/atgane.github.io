function [a, r2] = quadregr(x, y)

n = length(x);
if length(y) ~= n, error('x and y must be same length'); end
x = x(:); y = y(:);
sx = sum(x); sy = sum(y);
sx2 = sum(x.* x); 
sx3 = sum(x.^3);
sx4 = sum(x.^4);
sxy = sum(x.* y); sx2y = sum(x.*x.*y); sx3y = sum(x.*x.*x.*y);

A = [sx4 sx3 sx2; sx3 sx2 sx; sx2 sx n];
b = [sx2y sxy sy]';
disp(A);
a = A\b;

% r2 = ((n * sxy - sx * sy) / sqrt(n * sx2 - sx^2) / sqrt(n * sy2 - sy^2))^2;

sr = y - a(1) * x.^2 - a(2) * x - a(3);
st = y - sy / n;
Sr = sum(sr.*sr);
St = sum(st.*st);
r2 = (St - Sr) / St;

xp = linspace(min(x), max(x), 20);
yp = a(1) * xp.^2 + a(2) * xp + a(3);
plot(x, y, 'o', xp, yp);
grid on
end