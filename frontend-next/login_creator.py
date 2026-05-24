import tkinter as tk
from tkinter import messagebox
from supabase import create_client, Client
import hashlib

# Configurações do Supabase
SUPABASE_URL = ""  
SUPABASE_KEY = ""          

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Função para gerar hash da senha
def gerar_hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

# Função para cadastrar usuário
def cadastrar_usuario():
    nome = entry_nome.get().strip()
    email = entry_email.get().strip()
    senha = entry_senha.get().strip()

    if not nome or not email or not senha:
        messagebox.showwarning("Aviso", "Preencha todos os campos!")
        return

    senha_hash = gerar_hash_senha(senha)

    try:
        response = supabase.table("usuarios").insert({
            "nome_completo": nome,
            "email": email,
            "senha_hash": senha_hash
        }).execute()

        if response.data:
            messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")
            entry_nome.delete(0, tk.END)
            entry_email.delete(0, tk.END)
            entry_senha.delete(0, tk.END)
        else:
            messagebox.showerror("Erro", f"Erro ao cadastrar: {response}")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha na conexão ou inserção:\n{e}")

# Criando interface Tkinter
root = tk.Tk()
root.title("Cadastro de Usuários")
root.geometry("400x300")
root.resizable(False, False)

# Widgets
label_nome = tk.Label(root, text="Nome Completo:")
label_nome.pack(pady=5)
entry_nome = tk.Entry(root, width=40)
entry_nome.pack(pady=5)

label_email = tk.Label(root, text="Email:")
label_email.pack(pady=5)
entry_email = tk.Entry(root, width=40)
entry_email.pack(pady=5)

label_senha = tk.Label(root, text="Senha:")
label_senha.pack(pady=5)
entry_senha = tk.Entry(root, show="*", width=40)
entry_senha.pack(pady=5)

btn_cadastrar = tk.Button(root, text="Cadastrar", command=cadastrar_usuario, bg="#4CAF50", fg="white", width=15)
btn_cadastrar.pack(pady=20)

# Rodar interface
root.mainloop()
