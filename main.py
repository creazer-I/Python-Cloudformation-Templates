# reverse a number 

'''num = 188

rev = 0

def revv(num,rev):
	while num!=0:

		rev = rev*10 + num%10
		num = num//10
	return rev

print(revv(num,rev))'''

# Write a program in Python to check given number is prime or not.

'''def check_prime(num):
	for i in range(2,num):
		if num%i ==0:
			return False
	else:
		return True


for i in range(1,100):
	if i > 1:
		prime = check_prime(i)

		if prime == True:
			print(i,"Prime")
		else:
			print(i,"Not Prime")'''


# print prime numbers


'''for prime in range(1,100):
	if prime > 1:
		for i in range(2, prime):
			if prime % i == 0:
				break
		else:
			print(prime, end= '/') '''


# factorial

'''def fact(n = 5):
	result  = 1
	for i in range(1,n+1):
		result *= i
	print(result)


fact() '''


# fibo using recursive
'''def fib(a = 0, b= 1, series = 10):
	if a == 0 and b == 1:
		print(a)
		print(b)
	if b < series:
		print(a + b)
		fib(b , a+b, series)

fib()'''

# fibo using iterative/ recursive

'''def fibo(a = 0,b = 1, series = 10):
	if a == 0 and b == 1:
		print(a)
		print(b)
	if b < series:
		print(a+b)
		fibo(b, a+b,series)

fibo()
'''
# iterative

'''a, b = 0,1
num = 10
series = 0

for i in range(num):
	print(series, end = '|')
	a, b = b, series
	series = a+'''

# Palindrome
'''
num = 981

reverse = 0
temp = num

while temp!=0:
	reverse = reverse*10 + temp%10
	temp = temp//10

if num == reverse:
	print("Palindrome")

else:
	print("Not Palindrome")'''

# reverse a string

'''str = 'Mahendra'

reverse = ''

for i in str:
	reverse = i + reverse

print(reverse)'''

#Write a program in Python to find greatest among three integers.
'''
a = 10
b = 20
c = 15

if a < b:
	print(a)
elif b < c:
	print(b)
else:
	print(c)'''

'''a = [10,20,35]

print(max(a))'''
	
#class

'''class person:
	def __init__(self, name):
		self.name = name

	def names(self):
		print('My Name is',self.name)


pe = person('Mahendra')
pe.names()'''

# decorator

'''def decorator(func):
	def wrapper():
		print('added')
		func()
		print('function')

	return wrapper

@decorator
def fun():
	print('Mahendra')

fun()'''

# sum

#find duplicates in the array

'''arr =  [1,3,3,2,5,4,5]

duplicates = []
non_duplicates = []
count = {}

for i in arr:
	if i in non_duplicates:
		duplicates.append(i)
		count[i] += 1
	else:
		non_duplicates.append(i)
		count[i] = 1


print(duplicates,non_duplicates)
print(count)'''


# fibo

''' def fibo(a = 0,b = 1,series = 10):
	if a == 0 and b == 1:
		print(a)
		print(b)
	if b < series:
		print(a+b)
		fibo(b,a+b,series)

fibo()'''

'''a,b = 0,1
fibo_till= 10
series  = 0

for i in range(fibo_till):
	print(series,end = "|")
	a,b = b,series
	series = a+b'''

#factorial
'''
def fact(num = 5):
	result  = 1
	for i in range(1,num+1):
		result *= i
		
	return result

print(fact())


import math
a = 5

print(math.factorial(a))'''


'''a = [1,2,3,4]

l = tuple(a)

print(l)

print(type(l))

g = list(a)

g.append('ab')

again = tuple(g)
print(again)
print(type(again))'''

'''a = 'Mahendra'
result = ''
for s in a:
	if s not in ('a','e','i','o','u','A','E','I','O','U'):
		result += s


print(result)

'''

'''a = [1,2,1,2,3]

print(a)

unique = list(set(a))

print(unique)'''

'''a ='Mahendra'
count = 0
for i in a:
	count += len(i)

print(count)'''

'''a = 'Mahendra'

print(a[1:3])'''


'''a = {i : i + 1 for i in range(5)}

print(a)'''

'''a = [1,2,3,4]

print(a[1:3])'''

'''try:
	print('1' + 'q')
except:
	print('e')
else:
	print('something')
finally:
	print('hello')
'''

'''a = (1,2)

b = (3,4)

c = list(a)
for i in b:
	c.append(i)

print(tuple(c))'''


'''for i in range(1,11):
	print('2 x',i,2*i)'''


'''class employee:
	def __init__(self,name,no):
		self.name = name
		self.no = no

	def details(self):
		print('Epl name is :',self.name,'and no is :',self.no)


p = employee('Mahendra',141)

p.details()'''

'''import json

with open('file.json') as f:
	data = json.loads(f)

print(data['name'])
print(data['age'])'''


#fact


'''def fact(a = 1):
	result = 1
	for i in range(1,a+1):
		result *= i
	return result

print(fact())'''

# prime list

'''series = 100
lists = []

for i in range(series):
	if i > 1:
		for j in range(2,i):
			if i %j == 0:
				break
		else:
			lists.append(i)

print(lists)'''

#fibo

'''a = 0 
b = 1
series = 10
fibo = 0


for i in range(series):
	print(fibo,end = "|")
	a = b
	b = fibo
	fibo = a + b'''
# class

'''class person:
	def __init__(self,name,age):
		self.name = name 
		self.age = age

	def intro(self):
		print('My names',self.name,'and my age is',self.age)

p = person('Mahendra',25)
p.intro()'''

# decorator

'''def decor(func):
	def wrapper():
		print('a')
		func()
		print('b')
	return wrapper

@decor
def funv():
	print('dfjdshvfisuohifsubiw')

funv()'''


# recursive fibo


'''def fib(a= 0, b = 1, series = 10):
	if a == 0 and b == 1:
		print(a)
		print(b)
	if b < series:
		print(a+b)
		fib(b,a+b, series)

fib()'''


a= [1,2,3,4,45]

print(a.pop(1))