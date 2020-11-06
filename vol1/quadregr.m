function [a, r2] = cubregr(x, y)

n = length(x);
if length(y) ~= n, error('x and y must be same length'); end
x = x(:); y = y(:);
sx = sum(x); sy = sum(y);
sx1 =sx;
sx2 = sum(x.* x); 
sx3 = sum(x.^3);
sx4 = sum(x.^4);
sx5 = sum(x.^5);
sx6 = sum(x.^6);
sxy = sum(x.* y); sx2y = sum(x.*x.*y); sx3y = sum(x.*x.*x.*y);

A = [sx6 sx5 sx4 sx3; sx5 sx4 sx3 sx2; sx4 sx3 sx2 sx1; sx3 sx2 sx1 n];
b = [sx3y sx2y sxy sy]';
disp(A);
a = A\b;

% r2 = ((n * sxy - sx * sy) / sqrt(n * sx2 - sx^2) / sqrt(n * sy2 - sy^2))^2;

sr = y - a(1) * x.^3 - a(2) * x.^2 - a(3) * x- a(4);
st = y - sy / n;
Sr = sum(sr.*sr);
St = sum(st.*st);
r2 = (St - Sr) / St;

xp = linspace(min(x), max(x), 20);
yp = a(1) * xp.^3 + a(2) * xp.^2 + a(3) * xp + a(4);
plot(x, y, 'o', xp, yp);
grid on
end