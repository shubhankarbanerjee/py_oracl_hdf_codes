# Tower of Hanoi


def display_towers():
    global tower_s,tower_l,line_char
    lA=max(tower_l[0] ,default=0) +1
    lB=max(tower_l[1] ,default=0) +1
    lC=max(tower_l[2] ,default=0) +1
    lA=lB=lC=max(lA,lB,lC)
    for i in range(max(tower_s[0],tower_s[1],tower_s[2])):
        line=''
        if i<tower_s[0]:
            x=tower_l[0][i]
        else:
            x=0
        for j in range (lA) :
            if j<x:
                line +=line_char
            else :
                line +=' ' 
        if i<tower_s[1]:
            x=tower_l[1][i]
        else:
            x=0
        for j in range (lB) :
            if j<x:
                line +=line_char
            else :
                line +=' '
        if i<tower_s[2]:
            x=tower_l[2][i]
        else:
            x=0
        for j in range (lC) :
            if j<x:
                line +=line_char
            else :
                line +=' '
        print(line)

def move_tower(tower_from,tower_to,tower_ext,num_disc):
    global tower_s,tower_l,num_of_steps
    #print("Step :"+str(num_of_steps+1)+":\tMove "+str(num_disc)+" from "+str(tower_from)+" to "+str(tower_to)+".")
    print("Step :%d :\t Move %d discs from Tower %d to Tower %d."\
          %(num_of_steps+1,num_disc,tower_from,tower_to))
    if(num_disc>1):
        move_tower(tower_from,tower_ext,tower_to,num_disc-1)
        move_tower(tower_from,tower_to,tower_ext,1)
        move_tower(tower_ext,tower_to,tower_from,num_disc-1)
    elif(num_disc==1):
        if tower_s[tower_from]>=0:
            num_of_steps+=1
            tower_s[tower_from] -=1
            x = tower_l[tower_from].pop()
            tower_s[tower_to] +=1
            tower_l[tower_to].append(x)
            display_towers()
    else:
        print("Error encountered !")
        return False

while('0'!=input("Would you like to play tower of Hanoi game? (0 for no):") ):
    number_of_disc=int(input('Number of Disc on Tower A:') )
    if number_of_disc>5000 :
        exit
    tower_s=[number_of_disc,0,0]
    tower_l=[[],[],[]]
    num_of_steps=0
    line_char=input("Any thing that can represent a disc:")
    #initialize tower A
    for i in range(number_of_disc,0,-1):
        tower_l[0].append(i)
        
    display_towers()
    move_tower(0,2,1,number_of_disc)
