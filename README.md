#  AÇAI - Banco de Dados Cromatográficos

Plataforma para análise e identificação de compostos em alimentos através de dados cromatográficos (HPLC/GC-MS). Desenvolvido pelo **PPGCTA/UFPel**.

![Logo do Projeto](static/image/logodb3.png)

## Funcionalidades
- Cadastro de compostos químicos (massas, tempos de retenção, matrizes alimentares)
- Identificação automática por modelos de Machine Learning
- Busca avançada por massa molecular, nome ou características
- Visualização de dados analíticos e cromatogramas
- Dashboard interativo

## Tecnologias
- **Backend**: Python (Flask, SQLAlchemy)
- **Frontend**: HTML/CSS + Jinja2
- **ML**: scikit-learn (Random Forest, SVM)
- **Banco de Dados**: SQLite (dev) / PostgreSQL (prod)

## Instalação

### Pré-requisitos
- Python 3.10+
- Git

### Passo a Passo
```bash
# Clone o repositório
git clone https://github.com/seu-usuario/projeto-acai.git
cd projeto-acai

# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente (crie um arquivo .env)
echo "FLASK_APP=app.py" > .env
echo "FLASK_ENV=development" >> .env
echo "SECRET_KEY=sua_chave_secreta_aqui" >> .env

# Execute as migrações do banco
flask db upgrade

# Inicie o servidor
flask run

Acesse no navegador:
http://localhost:5000
