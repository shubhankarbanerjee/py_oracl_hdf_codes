#python Test file
import web, collections
urls=('/hello','index', '/(.*)', 'newClassName')
app= web.application(urls,globals())

class index:
	def GET(self):
		n_web=web.input(name="Your name ?")
		name=n_web.name
		greeting="HEllo "+name+"*2="+name*2 +'\nit contains '+ str(collections.Counter(name.lower()) )
		return greeting
		
if __name__=="__main__":
	app.run()

class newClassName:
	def GET(self,name):
		greeting="HEllo "+name+"*5="+name*5 +'\nit contains '+ str(collections.Counter(name.lower()) )
		return greeting
		
if __name__=="__main__":
	app.run()