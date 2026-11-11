

class Toque():
    
    def __init__(self,USD,EUR,MN,txt=None):
        self.USD = USD
        self.EUR = EUR
        self.MN = MN
        self.moneda = txt
    def Priority_values(self,p_usd):
        self.USD = p_usd

    def obtener_valor_dia(self,txt):
        if txt == "USD" or "usd":
            return self.USD
        
        
    





class Change():
    def __init__(self, moneda, change_tax, value):
        self.moneda = moneda
        self.change_tax = change_tax
        self.value = value
        
        
    def Change_USD_to_MN(self):
        if self.moneda == "USD":
            return self.value * self.change_tax
        
    def Change_MN_to_USD(self):
        if self.moneda == "MN":
            return self.value / self.change_tax
    
    def change_EUR_to_MN(self):
        if self.moneda == "MN":
            return self.value * self.change_tax
    
    
            
    def Change_EUR_to_USD(self):
        print("En proceso de Desasrrollo...")
        
        
           
        
        
if __name__=='__main__':

    usd_priority_value = int(input("Valor del dolar hoy... "))
    t1=Toque(usd_priority_value,950,1)
    
    print("="*60)
    print("DIA : ",t1.obtener_valor_dia("usd"))
    
    
    if usd_priority_value > 0:
        changeT = Toque(usd_priority_value,850,1)
    else:
        changeT = Toque(810,850,1)
            
    c1 = Change("USD", changeT.USD, 200)
    mn1 = Change("MN",changeT.USD,9000)
    
    value_in_mn = c1.Change_USD_to_MN()
    value_in_usd = mn1.Change_MN_to_USD()
    
    print("El valor a pagar en MN es  ", value_in_mn)
    print("El valor en dolares es : ",value_in_usd)
    c1.Change_EUR_to_USD()