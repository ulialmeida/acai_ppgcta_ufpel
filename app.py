from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, INTEGER, or_, and_, cast, Float, func
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from sqlalchemy.orm.exc import NoResultFound
from flask_migrate import Migrate
from sqlalchemy.orm import relationship
import pandas as pd
from sqlalchemy import inspect
from werkzeug.utils import secure_filename
from urllib.request import urlopen
from urllib.parse import quote
from collections import Counter
import os
import tempfile
import shutil
import json
import logging
import requests
import io
from io import BytesIO
import joblib



# Cria uma instância da aplicação Flask, inicializando aplicação web
app = Flask(__name__)
app.secret_key = "bancodedadosdecompostos123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/almei/PycharmProjects/banco_compostos/compounds.db'

modelo = joblib.load('modelo_composto.pkl')
scaler = joblib.load('scaler.pkl')
nomes = pd.read_csv('dicionario_nomes.csv')

db = SQLAlchemy(app)

app.config['DEBUG'] = True 

migrate = Migrate(app, db)

print("Banco em uso:", os.path.abspath("compounds.db"))

import requests
try:
    response = requests.get('https://pubchem.ncbi.nlm.nih.gov', timeout=5)
    print("Conectado ao PubChem com sucesso!")
except Exception as e:
    print(f"Falha na conexão: {str(e)}")


# Inicializar o Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Configuração detalhada de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flask_app.log'),
        logging.StreamHandler()
    ]
)

# Definição dos modelos SQLAlchemy para as tabelas do banco de dados
class Compound(db.Model):
    __tablename__ = 'tbl_compound' 
    compound_id = db.Column(db.Integer, primary_key=True)
    compound = db.Column(db.String(255))
    molecular_formula = db.Column(db.String(255))
    molecular_mass = db.Column(db.Float)
    pubchem_cid = db.Column(db.String(50))  # ID do PubChem
    pubchem_url = db.Column(db.String(255))  # URL direta para o composto

    def fetch_pubchem_data(self):
        """Busca automaticamente dados do PubChem baseado no nome do composto"""
        try:
            base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            encoded_name = quote(self.compound.strip().lower())  # Normaliza o nome

            # Tentativa 1: Busca exata
            url = f"{base_url}{encoded_name}/JSON"
            
            with urlopen(url) as response:
                data = json.loads(response.read().decode())

                # Verifica diferentes estruturas de resposta
                if 'PC_Compounds' in data:
                    cid = str(data['PC_Compounds'][0]['id']['id']['cid'])
                elif 'IdentifierList' in data:
                    cid = str(data['IdentifierList']['CID'][0])
                else:
                    raise ValueError("Estrutura de resposta inesperada")
                
                self.pubchem_cid = cid
                self.pubchem_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
                return True
                
        except Exception as e:
            print(f"Erro na busca por nome exato: {str(e)}")
            # Tentativa 2: Busca por substring se a exata falhar
            try:
                url = f"{base_url}{encoded_name}/JSON?name_type=word"
                with urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    if 'IdentifierList' in data and data['IdentifierList']['CID']:
                        self.pubchem_cid = str(data['IdentifierList']['CID'][0])
                        self.pubchem_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{self.pubchem_cid}"
                        return True
            except Exception as fallback_e:
                print(f"Erro na busca por palavra: {str(fallback_e)}")
        
        return False

    def fetch_by_formula(self):
        """Busca no PubChem por fórmula molecular quando o nome falha"""
        try:
            if not self.molecular_formula:
                return False
                
            base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/"
            encoded_formula = quote(self.molecular_formula)
            url = f"{base_url}{encoded_formula}/cids/JSON"
            
            with urlopen(url) as response:
                data = json.loads(response.read().decode())
                if 'IdentifierList' in data and data['IdentifierList']['CID']:
                    self.pubchem_cid = str(data['IdentifierList']['CID'][0])
                    self.pubchem_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{self.pubchem_cid}"
                    return True
        except Exception as e:
            print(f"Erro ao buscar por fórmula: {str(e)}")
        return False      

    def fetch_pubchem_info(self):
            """Tenta buscar informações no PubChem usando nome e depois fórmula molecular"""
            if self.fetch_pubchem_data():  # Tenta pelo nome primeiro
                return True
            return self.fetch_by_formula()  # Fallback para fórmula molecular
                
class Matrix(db.Model):
    __tablename__ = 'tbl_matrixes'
    matrixes_id = db.Column(db.Integer, primary_key=True)
    organism = db.Column(db.String(255))
    plant_tissue = db.Column(db.String(255))

class Name(db.Model):
    __tablename__ = 'tbl_name'
    name_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    
class Identification(db.Model):
    __tablename__ = 'tbl_identification'
    compound_id = db.Column(db.Integer, ForeignKey('tbl_compound.compound_id'), primary_key=True)
    matrix_id = db.Column(db.Integer, ForeignKey('tbl_matrixes.matrixes_id'), primary_key=True)
    name_id = db.Column(db.Integer, ForeignKey('tbl_name.name_id'), primary_key=True)

class CompoundAnalytics(db.Model):
    __tablename__ = 'tbl_compound_analytics'


    analytics_id = db.Column(db.Integer, primary_key=True)
    compound_id = db.Column(db.Integer, db.ForeignKey('tbl_compound.compound_id'), nullable=False)
    retention_time = db.Column(db.Float, nullable=False)
    m_z = db.Column(db.Float, nullable=False)
    intensity = db.Column(db.Float, nullable=False)
    sigma = db.Column(db.Float)
    instrument_method = db.Column(db.String(100), nullable=False)
    matrix_id = db.Column(db.Integer, db.ForeignKey('tbl_matrixes.matrixes_id'))
    compound_class = db.Column(db.String(50)) 
    ionization_mode = db.Column(db.String(10)) 
    collision_energy = db.Column(db.Float)   
    fragment = db.Column(db.Float)  
    method_description = db.Column(db.String(255))
    chromatographic_condition = db.Column(db.String(255))
    notes = db.Column(db.Text)

    # Relacionamentos
    compound = db.relationship('Compound', backref='analytics')
    matrix = db.relationship('Matrix', backref='analytics')
    fragments = db.relationship('Fragment', back_populates='compound_analytics', cascade='all, delete-orphan')

class Fragment(db.Model):
    __tablename__ = 'fragments'
    
    id = db.Column(db.Integer, primary_key=True)
    m_z = db.Column(db.Float, nullable=False)
    intensity = db.Column(db.Float, nullable=False)
    compound_analytics_id = db.Column(db.Integer, db.ForeignKey('tbl_compound_analytics.analytics_id'), nullable=False)

    # Relacionamento reverso
    compound_analytics = db.relationship('CompoundAnalytics', back_populates='fragments')


# Definição da classe User para autenticação
class User(UserMixin, db.Model):
    __tablename__ = 'tbl_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))

# Configuração para uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Rotas para exibição e interação com os dados
@app.route('/')
def entrada():
    return render_template('entrada.html', login_url=url_for('login'))  


@app.route('/compound')
def index():
    compounds = Compound.query.all()
    return render_template('index.html', compounds=compounds)

@app.route('/matrixes')
def matrixes():
    matrixes = Matrix.query.all()
    if len(matrixes) == 0:
        return 'A tabela `tbl_matrixes` está vazia.'
    else:
        return render_template('matrixes.html', matrixes=matrixes)
    
@app.route('/name')
def name():
    names = Name.query.all()
    if len(names) == 0:
        return 'A tabela `tbl_name` está vazia.'
    else:
        return render_template('name.html', names=names)

@app.route('/identification')
def identification():
    identifications = Identification.query.all()
    if len(identifications) == 0:
        return 'A tabela `tbl_identification` está vazia.'
    else:
        return render_template('identification.html', identifications=identifications)
    
@app.route('/analytics')
def analytics_view():
    try:
        # Carrega todos os dados necessários em uma única consulta
        analytics = db.session.query(CompoundAnalytics).options(
            db.joinedload(CompoundAnalytics.compound),
            db.joinedload(CompoundAnalytics.matrix)
        ).order_by(CompoundAnalytics.analytics_id.desc()).all()
        
        if not analytics:
            flash("Nenhuma análise encontrada no banco de dados", "info")

        return render_template('analytics.html',
            analytics=analytics,
            compounds=Compound.query.all(),
            matrixes=Matrix.query.all())
            
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar análises: {str(e)}")
        flash("Ocorreu um erro ao carregar as análises", "danger")
        return redirect(url_for('index'))
    
@app.route('/view_compound/<int:compound_id>')
def view_compound(compound_id):
    # Recupera o composto
    compound = Compound.query.get_or_404(compound_id)

    # Para buscar dados adicionais do PubChem
    pubchem_data = {}
    if compound.pubchem_cid:
        pubchem_data = get_pubchem_data(compound.pubchem_cid)
    
    # Recupera TODAS as identificações relacionadas
    identifications = db.session.query(
        Identification,
        Matrix,
        Name
    ).join(
        Matrix, Identification.matrix_id == Matrix.matrixes_id
    ).join(
        Name, Identification.name_id == Name.name_id
    ).filter(
        Identification.compound_id == compound_id
    ).all()
    
    return render_template(
        'view_compound.html',
        compound=compound,
        identifications=identifications,
        pubchem_data=pubchem_data
    )

@app.route('/get_pubchem_data/<cid>')
def get_pubchem_data(cid):
    try:
        url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/CanonicalSMILES,InChIKey,CAS,IUPACName/JSON'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        return jsonify({
            'status': 'success',
            'cas': data['PropertyTable']['Properties'][0].get('CAS', ''),
            'smiles': data['PropertyTable']['Properties'][0].get('CanonicalSMILES', ''),
            'inchi_key': data['PropertyTable']['Properties'][0].get('InChIKey', ''),
            'iupac_name': data['PropertyTable']['Properties'][0].get('IUPACName', '')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/buscar_compostos')
def buscar_compostos():
    return render_template('buscar_compostos.html')

@app.route('/formulario')
def formulario_fragmentos():
    return render_template('formulario.html')

@app.route('/buscar_por_massa', methods=['GET', 'POST'])
def buscar_por_massa():
    resultados = None
    if request.method == 'POST':
        massa = float(request.form['massa'])
        resultados = buscar_compostos_bd(massa)  # sua função
    return render_template('buscar_massas.html', resultados=resultados)

def fetch_by_cid(cid):
    """Busca direta por CID com tratamento robusto"""
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/JSON"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return parse_pubchem_response(data, cid)
        
    except requests.exceptions.RequestException as e:
        return {
            'status': 'error',
            'message': f'Falha na conexão com o PubChem: {str(e)}',
            'solution': 'Verifique o CID ou sua conexão com a internet'
        }

def fetch_by_name(name):
    """Busca por nome apenas para nomes simples"""
    try:
        # Faz encoding seguro do nome
        encoded_name = quote(name.strip().lower())
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/JSON"
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Se a resposta contiver CIDs, pega o primeiro e busca por CID
        if 'IdentifierList' in data and data['IdentifierList']['CID']:
            cid = data['IdentifierList']['CID'][0]
            return fetch_by_cid(cid)
            
        return {
            'status': 'not_found',
            'message': 'Composto não encontrado por nome',
            'solution': 'Tente buscar pelo CID diretamente'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'solution': 'Use o campo PubChem CID para busca direta'
        }

def parse_pubchem_response(data, cid):
    """Processa a resposta da API do PubChem"""
    try:
        if 'PC_Compounds' not in data:
            return {'status': 'no_data', 'message': 'Estrutura de dados inesperada'}
        
        compound = data['PC_Compounds'][0]
        props = {}
        
        # Processa propriedades
        for prop in compound.get('props', []):
            label = prop.get('label', {}).get('name', '')
            value = prop.get('value', {}).get('sval', '')
            if label and value:
                props[label] = value
        
        # Calcula fórmula molecular
        formula = ''
        if 'atoms' in compound and 'elements' in compound['atoms']:
            elements = compound['atoms']['elements']['eid']
            formula = ''.join(f"{el}{count if count > 1 else ''}" 
                           for el, count in sorted(Counter(elements).items()))
        
        return {
            'cid': cid,
            'cas': props.get('CAS', ''),
            'smiles': props.get('Canonical SMILES', ''),
            'inchi_key': props.get('InChIKey', ''),
            'iupac_name': props.get('IUPAC Name', ''),
            'molecular_formula': formula,
            'molecular_weight': compound.get('charge', {}).get('molecular_weight', 0),
            'source': 'PubChem',
            'status': 'success',
            'pubchem_url': f'https://pubchem.ncbi.nlm.nih.gov/compound/{cid}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Erro ao processar resposta: {str(e)}',
            'cid': cid
        }



def buscar_compostos_bd(massa_alvo, tolerancia=50.0):
    massa_min = massa_alvo - tolerancia
    massa_max = massa_alvo + tolerancia

    compostos = Compound.query.filter(
        Compound.molecular_mass != None,
        cast(Compound.molecular_mass, Float) >= massa_min,
        cast(Compound.molecular_mass, Float) <= massa_max
    ).all()

    resultados = []
    for c in compostos:
        try:
            massa = float(c.molecular_mass)
            diferenca = abs(massa - massa_alvo)
            resultados.append({
                'compound_name': c.compound,
                'molecular_mass': massa,
                'diferenca': diferenca
            })
        except ValueError:
            continue

    resultados = sorted(resultados, key=lambda x: x['diferenca'])
    return resultados


@app.route('/view_author_compounds/<int:author_id>')
def view_author_compounds(author_id):
    # Recupera o autor com base no ID
    author = Name.query.get(author_id)

    if not author:
        return 'Autor não encontrado.'

    # Recupera as identificações relacionadas a este autor
    identifications = Identification.query.filter_by(name_id=author_id).all()

    # Recupera informações relacionadas aos compostos usando os IDs das identificações
    compounds_info = []

    for identification in identifications:
        compound = Compound.query.get(identification.compound_id)
        if compound:
            compounds_info.append(compound)

    return render_template('view_author_compounds.html', author=author, compounds_info=compounds_info)

@app.route('/view_matrix_compounds/<int:matrix_id>')
def view_matrix_compounds(matrix_id):
    # Recupera o organismo com base no ID
    matrix = Matrix.query.get(matrix_id)

    if not matrix:
        return 'Organismo não encontrado.'

    # Recupera as identificações relacionadas a este organismo
    identifications = Identification.query.filter_by(matrix_id=matrix_id).all()

    # Recupera informações relacionadas aos compostos usando os IDs das identificações
    compound_info = []

    for identification in identifications:
        compound = Compound.query.get(identification.compound_id)

        if compound:
            compound_info.append(compound)

    return render_template('view_matrix_compounds.html', matrix=matrix, compound_info=compound_info)

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

     # Verifica se as credenciais estão corretas
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            login_user(user)  # Autentica o usuário
            return redirect(url_for('entrada'))

    return render_template('login.html')   

#Adição de novas informações 
@app.route('/add_compound', methods=['POST'])
@login_required
def add_compound():
    try:
        compound_name = request.form['compound']
        formula = request.form['molecular_formula']
        mass = float(request.form['molecular_mass'])
        
        print(f"Tentando adicionar: {compound_name}")  # Debug no terminal
        
        # Verificação robusta de duplicatas
        existing = Compound.query.filter(
            db.or_(
                Compound.compound == compound_name,
                db.and_(
                    Compound.molecular_formula == formula,
                    Compound.molecular_mass == mass
                )
            )
        ).first()
        
        if existing:
            msg = f"Erro: Composto '{compound_name}' ou fórmula idêntica já existe!"
            print(msg)  # Aparece no terminal
            flash(msg, 'error')
            return redirect(url_for('index'))
            
        new_compound = Compound(
            compound=compound_name,
            molecular_formula=formula,
            molecular_mass=mass
        )
        
        # Tenta buscar dados do PubChem antes de salvar
        pubchem_success = new_compound.fetch_pubchem_info()
        
        if not pubchem_success:
            flash(f"Aviso: Não foi possível encontrar '{compound_name}' no PubChem automaticamente. "
                  f"Você pode editar o composto posteriormente para adicionar manualmente.", 'warning')
        
        db.session.add(new_compound)
        db.session.commit()
        
        flash(f"Sucesso: '{compound_name}' adicionado!" + 
              (" Dados do PubChem incluídos automaticamente." if pubchem_success else ""), 
              'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        print(f"ERRO: {str(e)}")  # Debug no terminal
        flash("Erro interno ao processar o composto", 'error')
        return redirect(url_for('index'))
    
@app.route('/fetch_pubchem/<int:compound_id>')
@login_required
def fetch_pubchem(compound_id):
    compound = Compound.query.get_or_404(compound_id)
    if compound.fetch_pubchem_info():
        db.session.commit()
        flash('Dados do PubChem atualizados com sucesso!', 'success')
    else:
        flash('Não foi possível encontrar informações no PubChem. Preencha manualmente.', 'warning')
    return redirect(url_for('edit_compound', compound_id=compound_id))

@app.route('/add_matrix', methods=['POST'])
@login_required
def add_matrix():
    organism = request.form['organism']
    plant_tissue = request.form['plant_tissue']
    
    new_matrix = Matrix(organism=organism, plant_tissue=plant_tissue)
    db.session.add(new_matrix)
    db.session.commit()
    
    return redirect(url_for('matrixes'))

@app.route('/add_name', methods=['POST'])
@login_required
def add_name():
    name = request.form['name']
    
    new_name = Name(name=name)
    db.session.add(new_name)
    db.session.commit()
    
    return redirect(url_for('name'))

@app.route('/add_identification', methods=['POST'])
@login_required
def add_identification():
    try:
        compound_id = int(request.form['compound_id'])
        matrix_id = int(request.form['matrix_id'])
        name_id = int(request.form['name_id'])
    except ValueError:
        flash('IDs devem ser números inteiros válidos!', 'error')
        return redirect(url_for('identification'))

    # Verifica se a identificação já existe PRIMEIRO
    if Identification.query.filter_by(
        compound_id=compound_id,
        matrix_id=matrix_id,
        name_id=name_id
    ).first():
        flash('Esta identificação já existe no banco de dados!', 'error')
        return redirect(url_for('identification'))

    # Verifica se os IDs existem nas tabelas
    try:
        Compound.query.filter_by(compound_id=compound_id).one()
        Matrix.query.filter_by(matrixes_id=matrix_id).one()
        Name.query.filter_by(name_id=name_id).one()
    except NoResultFound:
        flash('Composto, matriz ou nome não encontrado!', 'error')
        return redirect(url_for('identification'))

    # Se tudo certo, adiciona
    new_id = Identification(
        compound_id=compound_id,
        matrix_id=matrix_id,
        name_id=name_id
    )
    db.session.add(new_id)
    db.session.commit()
    flash('Identificação adicionada com sucesso!', 'success')
    return redirect(url_for('identification'))

@app.route('/add_analytic', methods=['POST'])
@login_required
def add_analytic():
    try:
        print("Dados recebidos:", request.form)

        compound_id = request.form['compound_id']
        matrix_id = request.form['matrix_id']
        instrument_method = request.form['instrument_method']
        fragments_mz = request.form.getlist('fragments[][m_z]')
        fragments_intensity = request.form.getlist('fragments[][intensity]')

        def parse_float(value):
            try:
                return float(value) if value else None
            except ValueError:
                return None

        retention_time = parse_float(request.form.get('retention_time'))
        m_z = parse_float(request.form.get('m_z'))
        intensity = parse_float(request.form.get('intensity'))
        sigma = parse_float(request.form.get('sigma'))
        collision_energy = parse_float(request.form.get('collision_energy'))
        compound_class = request.form.get('compound_class') or None
        ionization_mode = request.form.get('ionization_mode') or None
        method_description = request.form.get('method_description') or None
        chromatographic_condition = request.form.get('chromatographic_condition') or None
        notes = request.form.get('notes') or None

        # Cria o objeto da análise
        new_analytic = CompoundAnalytics(
            compound_id=compound_id,
            matrix_id=matrix_id,
            instrument_method=instrument_method,
            retention_time=retention_time,
            m_z=m_z,
            intensity=intensity,
            sigma=sigma,
            compound_class=compound_class,
            ionization_mode=ionization_mode,
            collision_energy=collision_energy,
            method_description=method_description,
            chromatographic_condition=chromatographic_condition,
            notes=notes
        )

        db.session.add(new_analytic)
        db.session.flush()  # Garante que o analytics_id será preenchido

        # Adiciona os fragmentos associados
        for mz, inten in zip(fragments_mz, fragments_intensity):
            parsed_mz = parse_float(mz)
            parsed_inten = parse_float(inten)
            if parsed_mz is not None and parsed_inten is not None:
                fragment = Fragment(
                    m_z=parsed_mz,
                    intensity=parsed_inten,
                    compound_analytics_id=new_analytic.analytics_id
                )
                db.session.add(fragment)

        db.session.commit()
        flash('Análise adicionada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        print("Erro ao salvar:", str(e))
        flash(f'Erro: {str(e)}', 'danger')

    return redirect(url_for('analytics_view'))



@app.route('/compound_analytics', methods=['GET', 'POST'])
@login_required
def compound_analytics():
    if request.method == 'POST':
        # Verificar se é upload de arquivo ou formulário manual
        if 'file' in request.files:
            return import_analytics()  # Usa a função melhorada acima
        else:
            # Processar formulário manual
            try:
                # Validar dados
                required_fields = [
                    'compound_id', 'matrix_id', 'retention_time',
                    'm_z', 'intensity', 'sigma', 'instrument_method'
                ]
                for field in required_fields:
                    if not request.form.get(field):
                        flash(f'Campo obrigatório faltando: {field}', 'error')
                        return redirect(url_for('analytics_view'))
                
                # Verificar duplicata
                exists = CompoundAnalytics.query.filter_by(
                    compound_id=int(request.form['compound_id']),
                    matrix_id=int(request.form['matrix_id']),
                    instrument_method=request.form['instrument_method']
                ).first()
                
                if exists:
                    flash('Esta análise já existe no banco de dados!', 'error')
                    return redirect(url_for('analytics_view'))
                
                # Criar nova análise
                new_analytic = CompoundAnalytics(
                    compound_id=int(request.form['compound_id']),
                    matrix_id=int(request.form['matrix_id']),
                    retention_time=float(request.form['retention_time']),
                    m_z=float(request.form['m_z']),
                    intensity=float(request.form['intensity']),
                    sigma=float(request.form['sigma']),
                    instrument_method=request.form['instrument_method']
                )
                
                db.session.add(new_analytic)
                db.session.commit()
                flash('Análise adicionada com sucesso!', 'success')
                
            except ValueError as e:
                flash(f'Dados inválidos: {str(e)}', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao adicionar análise: {str(e)}', 'error')
            
            return redirect(url_for('analytics_view'))
    
    # GET request - mostrar página normal
    return analytics_view()

@app.route('/analytic/<int:analytic_id>')
@login_required
def view_analytic(analytic_id):
    analytic = db.session.query(CompoundAnalytics).options(
        db.joinedload(CompoundAnalytics.compound),
        db.joinedload(CompoundAnalytics.matrix)
    ).get_or_404(analytic_id)
    
    return render_template('analytic_detail.html', 
                         analytic=analytic)

@app.route('/download_analytics_template')
def download_analytics_template():
    # Cria um DataFrame de exemplo
    data = {
        'compound_id': [1, 2],
        'matrix_id': [1, 2],
        'retention_time': [2.5, 3.1],
        'm_z': [287.0, 301.2],
        'intensity': [15000, 18000],
        'sigma': [0.2, 0.3],
        'instrument_method': ['HPLC-UV', 'LC-MS']
    }
    
    # Cria o DataFrame
    df = pd.DataFrame(data)
    
    # Cria um buffer de memória para o arquivo
    output = BytesIO()
    
    # Cria o arquivo Excel no buffer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dados', index=False)
        
        # Adiciona uma aba de instruções
        workbook = writer.book
        sheet = workbook.create_sheet("Instruções")
        sheet['A1'] = "Instruções para preenchimento:"
        sheet['A3'] = "compound_id: ID do composto (deve existir no banco)"
        sheet['A4'] = "matrix_id: ID da matriz (deve existir no banco)"
        sheet['A5'] = "retention_time: Tempo de retenção em minutos"
        sheet['A6'] = "m_z: Razão massa/carga"
        sheet['A7'] = "intensity: Intensidade do sinal"
        sheet['A8'] = "sigma: Desvio padrão do pico"
        sheet['A9'] = "instrument_method: Método instrumental usado"
    
    # Prepara o arquivo para download
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name='template_analytics.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
@app.route('/import_analytics', methods=['POST'])
@login_required
def import_analytics():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Tipo de arquivo não permitido. Use CSV ou Excel.'}), 400
    
    try:
        # Criar diretório temporário
        temp_dir = tempfile.mkdtemp()
        filepath = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(filepath)
        
        # Processar o arquivo
        try:
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath, engine='openpyxl')
        except Exception as e:
            return jsonify({'error': f'Erro ao ler arquivo: {str(e)}'}), 400
        
        # Verificar colunas obrigatórias
        required_columns = {
            'compound_id', 'matrix_id', 'retention_time',
            'm_z', 'intensity', 'sigma', 'instrument_method'
        }
        missing = required_columns - set(df.columns.str.lower())
        if missing:
            return jsonify({
                'error': f'Colunas obrigatórias faltando: {", ".join(missing)}',
                'template': url_for('download_analytics_template')  # Corrigido para apontar para a função correta
            }), 400
        
        # Processar linhas
        results = {
            'success': 0,
            'errors': [],
            'duplicates': 0
        }
        
        for idx, row in df.iterrows():
            try:
                # Verificar se já existe análise idêntica
                exists = CompoundAnalytics.query.filter_by(
                    compound_id=int(row['compound_id']),
                    matrix_id=int(row['matrix_id']),
                    instrument_method=str(row['instrument_method'])
                ).first()
                
                if exists:
                    results['duplicates'] += 1
                    continue
                
                # Criar nova análise
                new_analytic = CompoundAnalytics(
                    compound_id=int(row['compound_id']),
                    matrix_id=int(row['matrix_id']),
                    retention_time=float(row['retention_time']),
                    m_z=float(row['m_z']),
                    intensity=float(row['intensity']),
                    sigma=float(row['sigma']),
                    instrument_method=str(row['instrument_method'])
                )
                
                db.session.add(new_analytic)
                results['success'] += 1
                
            except ValueError as e:
                results['errors'].append(f'Linha {idx+2}: Valor inválido - {str(e)}')
            except Exception as e:
                results['errors'].append(f'Linha {idx+2}: Erro - {str(e)}')
        
        db.session.commit()
        
        # Montar resposta
        response = {
            'message': f"Importação concluída: {results['success']} análises adicionadas",
            'success': results['success'],
            'errors': results['errors'],
            'duplicates': results['duplicates']
        }
        
        if results['errors']:
            response['warning'] = f"{len(results['errors'])} erros encontrados"
        
        # Logging dentro da função onde response está definido
        logging.info(f"Início de importação por {current_user.username}")
        logging.info(f"Resultado: {response}")
        
        return jsonify(response)
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erro na importação: {str(e)}")
        return jsonify({'error': f'Erro no servidor: {str(e)}'}), 500
        
    finally:
        # Limpar arquivos temporários
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
@app.route('/delete_compound', methods=['POST'])
@login_required
def delete_compound():
    compound_id = request.form['compound_id']

    # Verifica se o composto com o compound_id fornecido existe no banco de dados
    compound = Compound.query.get(compound_id)
    
    if not compound:
        return 'Composto não encontrado.'  # Redireciona para uma página de erro
    
    # Exclui composto do bd
    db.session.delete(compound)
    db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/delete_matrix', methods=['POST'])
@login_required
def delete_matrix():
    matrix_id = request.form['matrix_id']

    # Verifica se o composto com o compound_id fornecido existe no banco de dados
    matrix = Matrix.query.get(matrix_id)
    
    if not matrix:
        return 'Composto não encontrado.'  # Redireciona para uma página de erro
    
    # Exclui composto do bd
    db.session.delete(matrix)
    db.session.commit()

    return redirect(url_for('matrixes'))

@app.route('/delete_name', methods=['POST'])
@login_required
def delete_name():
    name_id = request.form['name_id']

    # Verifica se o composto com o compound_id fornecido existe no banco de dados
    name = Name.query.get(name_id)
    
    if not name:
        return 'Composto não encontrado.'  # Redireciona para uma página de erro
    
    # Exclui composto do bd
    db.session.delete(name)
    db.session.commit()

    return redirect(url_for('name'))

@app.route('/delete_identification', methods=['POST'])
@login_required
def delete_identification():
    compound_id = request.form['compound_id']
    matrix_id = request.form['matrix_id']
    name_id = request.form['name_id']

    try:
        identification = Identification.query.filter_by(
            compound_id=compound_id,
            matrix_id=matrix_id,
            name_id=name_id
        ).one()
    except NoResultFound:
        return 'Identificação não encontrada. Operação cancelada.'

    db.session.delete(identification)
    db.session.commit()

    return redirect(url_for('identification'))  # Substitua por onde quiser redirecionar


UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_headers(headers):
    required = {'compound', 'molecular_formula'}
    missing = required - set(headers)
    if missing:
        raise ValueError(f"Colunas obrigatórias faltando: {', '.join(missing)}")

@app.route('/delete_fragment/<int:id>', methods=['GET'])
@login_required
def delete_fragment(id):
    try:
        fragment = Fragment.query.get_or_404(id)
        db.session.delete(fragment)
        db.session.commit()
        flash('Fragmento excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir fragmento: {str(e)}', 'danger')

    # Redireciona de volta para a página de edição da análise relacionada
    return redirect(url_for('edit_analytic', id=fragment.compound_analytics_id))


@app.route('/upload', methods=['GET', 'POST'])  # ← Aceita ambos os métodos
@login_required
def upload_file():
    if request.method == 'GET':
        # Exibe o formulário de upload (GET)
        return render_template('upload.html')  # Substitua pelo seu template
    
    # Lógica para POST (upload do arquivo)
    if 'file' not in request.files:
        flash('Nenhum arquivo enviado', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'error')
        return redirect(request.url)
    
    if not allowed_file(file.filename):
        flash('Use arquivos CSV ou Excel (.xlsx, .xls)', 'error')
        return redirect(request.url)

    try:
        # Ler o arquivo
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file, engine='openpyxl')

        # Verificar colunas obrigatórias
        required_columns = {'compound', 'molecular_formula', 'molecular_mass'}
        missing = required_columns - set(df.columns.str.lower())
        if missing:
            flash(f'Colunas obrigatórias faltando: {", ".join(missing)}', 'error')
            return redirect(request.url)

        # Processar cada linha
        success_count = 0
        for _, row in df.iterrows():
            try:
                # Limpar molecular_mass (remove "Â", "+", espaços, etc.)
                mass = str(row['molecular_mass']).strip().replace('Â', '').replace('+', '')
                
                # Verificar se o composto já existe (pelo nome ou fórmula)
                existing = Compound.query.filter(
                    db.or_(
                        Compound.compound == row['compound'],
                        Compound.molecular_formula == row['molecular_formula']
                    )
                ).first()
                
                if not existing:
                    new_compound = Compound (
                        compound=row['compound'],
                        molecular_formula=row['molecular_formula'],
                        molecular_mass=float(mass),  # Converte para float
                        retention_time=float(row.get('retention_time', 0)),  
                        m_z=float(row.get('m_z', 0)),                       
                        intensity=float(row.get('intensity', 0)),           
                        pubchem_id=row.get('pubchem_id', '')
                        )
                    
                    db.session.add(new_compound)
                    success_count += 1

            except ValueError as e:
                flash(f"Erro na linha {_ + 2}: Massa molecular inválida ('{row['molecular_mass']}')", 'error')
                continue
            except Exception as e:
                flash(f"Erro na linha {_ + 2}: {str(e)}", 'error')
                continue

        db.session.commit()
        flash(f"{success_count} compostos importados com sucesso!", 'success')
        return redirect(url_for('index'))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao processar arquivo: {str(e)}", 'error')
        return redirect(request.url)

@app.route('/edit_analytic/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_analytic(id):
    analytic = CompoundAnalytics.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            analytic.compound_id = request.form['compound_id']
            analytic.matrix_id = request.form['matrix_id']
            analytic.retention_time = float(request.form['retention_time'])
            analytic.m_z = float(request.form['m_z'])
            analytic.intensity = float(request.form['intensity'])
            analytic.sigma = float(request.form['sigma']) if request.form['sigma'] else None
            analytic.instrument_method = request.form['instrument_method']
            analytic.compound_class = request.form.get('compound_class')
            analytic.fragment = float(request.form['fragment']) if request.form['fragment'] else None
            analytic.ionization_mode = request.form.get('ionization_mode')
            analytic.collision_energy = float(request.form['collision_energy']) if request.form['collision_energy'] else None
            analytic.method_description = request.form.get('method_description')
            analytic.chromatographic_condition = request.form.get('chromatographic_condition')
            analytic.notes = request.form.get('notes')
            existing_ids = request.form.getlist('existing_fragments_id')
            existing_mzs = request.form.getlist('existing_fragments_mz')
            existing_intensities = request.form.getlist('existing_fragments_intensity')

            for frag_id, mz, intensity in zip(existing_ids, existing_mzs, existing_intensities):
                fragment = Fragment.query.get(int(frag_id))
                if fragment:
                    fragment.m_z = float(mz) if mz else None
                    fragment.intensity = float(intensity) if intensity else None
            
            # Adicionar novos fragmentos (caso o usuário tenha preenchido)
            new_mzs = request.form.getlist('new_fragment_mz[]')
            new_intensities = request.form.getlist('new_fragment_intensity[]')

            for mz, intensity in zip(new_mzs, new_intensities):
                if mz and intensity:
                    new_fragment = Fragment(
                        m_z=float(mz),
                        intensity=float(intensity),
                        compound_analytics_id=analytic.analytics_id
                    )
                    db.session.add(new_fragment)

            
            db.session.commit()
            flash('Análise atualizada com sucesso!', 'success')
            return redirect(url_for('analytics_view'))
        
        except ValueError as e:
            flash(f'Valores inválidos: {str(e)}', 'error')
        except Exception as e:
            flash(f'Erro ao atualizar: {str(e)}', 'error')
    
    return render_template('edit_analytic.html',  
                         analytic=analytic,
                         compounds=Compound.query.all(),
                         matrixes=Matrix.query.all())

@app.route('/delete_analytic/<int:id>', methods=['POST'])
@login_required
def delete_analytic(id):
    analytic = CompoundAnalytics.query.get_or_404(id)
    try:
        db.session.delete(analytic)
        db.session.commit()
        flash('Análise excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir análise: {str(e)}', 'danger')
    return redirect(url_for('analytics_view'))
        
@app.route('/search')
def search():
    search_term = request.args.get('q', '').strip()
    
    if not search_term:
        return redirect(url_for('index'))
    
    # Busca por nome OU fórmula molecular (case-insensitive)
    results = Compound.query.filter(
        db.or_(
            Compound.compound.ilike(f"%{search_term}%"),
            Compound.molecular_formula.ilike(f"%{search_term}%")
        )
    ).all()

    min_mass = request.args.get('min_mass')
    if min_mass:
        results = results.filter(Compound.molecular_mass >= float(min_mass))
    
    return render_template('search.html', 
                         results=results,
                         search_term=search_term)

@app.route('/add-relation', methods=['POST'])
def add_relation():
    try:
        # Obter dados do formulário
        compound_id = request.form['compound_id']
        
        # Lógica para organismo (selecionado ou novo)
        organism = (request.form['organism_select'] 
                   if 'organism_select' in request.form and request.form['organism_select'] != "_NEW_"
                   else request.form['organism_new'].strip().title())
        
        # Lógica para tecido (selecionado ou novo)
        plant_tissue = (request.form['tissue_select']
                       if 'tissue_select' in request.form and request.form['tissue_select'] != "_NEW_"
                       else request.form['tissue_new'].strip().title())
        
        # Lógica para pesquisador (selecionado ou novo)
        if 'researcher_select' in request.form and request.form['researcher_select'] != "_NEW_":
            researcher_id = request.form['researcher_select']
        else:
            new_researcher = Name(name=request.form['researcher_new'].strip().title())
            db.session.add(new_researcher)
            db.session.flush()
            researcher_id = new_researcher.name_id
        
        # ===== LÓGICA DE CRIAÇÃO DO RELACIONAMENTO =====
        # 1. Verificar se matriz existe ou criar
        matrix = Matrix.query.filter_by(
            organism=organism,
            plant_tissue=plant_tissue
        ).first()
        
        if not matrix:
            matrix = Matrix(
                organism=organism,
                plant_tissue=plant_tissue
            )
            db.session.add(matrix)
            db.session.flush()
        
        # 2. Criar relação
        new_relation = Identification(
            compound_id=compound_id,
            matrix_id=matrix.matrixes_id,
            name_id=researcher_id
        )
        db.session.add(new_relation)
        db.session.commit()
        
        flash('Relação criada com sucesso!', 'success')
        return redirect(url_for('view_compound', compound_id=compound_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar relação: {str(e)}', 'error')
        return redirect(url_for('show_relation_form'))
    
@app.route('/add-relation')
@app.route('/add-relation/<int:compound_id>')
def show_relation_form(compound_id=None):
    compounds = Compound.query.all()
    
    # Obter o composto selecionado (se existir)
    selected_compound = None
    if compound_id:
        selected_compound = next((c for c in compounds if c.compound_id == compound_id), None)
    
    return render_template(
        'add_relation.html',
        compounds=compounds,
        organisms=[org[0] for org in db.session.query(Matrix.organism.distinct()).all()],
        tissues=[tiss[0] for tiss in db.session.query(Matrix.plant_tissue.distinct()).all()],
        researchers=Name.query.all(),
        selected_compound=selected_compound  # Passa o objeto completo do composto
    )

@app.route('/edit_compound/<int:compound_id>', methods=['GET', 'POST'])
@login_required
def edit_compound(compound_id):
    compound = Compound.query.get_or_404(compound_id)
    
    if request.method == 'POST':
        try:
            # Validação básica
            if not request.form['compound'].strip():
                flash('Nome do composto é obrigatório', 'error')
                return redirect(url_for('edit_compound', compound_id=compound_id))
            
            # Verifica se já existe outro composto com o mesmo nome (exceto o atual)
            existing = Compound.query.filter(
                Compound.compound == request.form['compound'],
                Compound.compound_id != compound_id
            ).first()
            
            if existing:
                flash('Já existe um composto com este nome!', 'error')
                return redirect(url_for('edit_compound', compound_id=compound_id))
            
            # Atualiza os dados básicos
            compound.compound = request.form['compound'].strip()
            compound.molecular_formula = request.form['molecular_formula'].strip()
            compound.molecular_mass = float(request.form['molecular_mass'])
            
            # Atualiza os campos do PubChem (editáveis manualmente)
            pubchem_cid = request.form.get('pubchem_cid', '').strip()
            if pubchem_cid:
                compound.pubchem_cid = pubchem_cid
                compound.pubchem_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{pubchem_cid}"
            else:
                compound.pubchem_cid = None
                compound.pubchem_url = None
            
            db.session.commit()
            flash('Composto atualizado com sucesso!', 'success')
            return redirect(url_for('view_compound', compound_id=compound_id))
            
        except ValueError as e:
            flash(f'Valor inválido: {str(e)}', 'error')
            return redirect(url_for('edit_compound', compound_id=compound_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar composto: {str(e)}', 'error')
            return redirect(url_for('edit_compound', compound_id=compound_id))
    
    # GET request - mostra o formulário com os dados atuais
    identifications = Identification.query.filter_by(compound_id=compound_id).all()
    return render_template(
        'edit_compound.html', 
        compound=compound,
        identifications=identifications
    )

@app.route('/edit_matrix/<int:matrix_id>', methods=['GET', 'POST'])
@login_required
def edit_matrix(matrix_id):
    matrix = Matrix.query.get_or_404(matrix_id)
    
    if request.method == 'POST':
        matrix.organism = request.form['organism']
        matrix.plant_tissue = request.form['plant_tissue']
        db.session.commit()
        flash('Matrix updated successfully!', 'success')
        return redirect(url_for('matrixes'))
    
    return render_template('edit_matrix.html', matrix=matrix)

# Edição de Pesquisador
@app.route('/edit_name/<int:name_id>', methods=['GET', 'POST'])
@login_required
def edit_name(name_id):
    name = Name.query.get_or_404(name_id)
    
    if request.method == 'POST':
        try:
            new_name = request.form['name'].strip()
            if not new_name:
                flash('O nome não pode estar vazio!', 'error')
                return redirect(url_for('edit_name', name_id=name_id))
            
            # Verifica se já existe outro pesquisador com o mesmo nome
            existing = Name.query.filter(
                Name.name == new_name,
                Name.name_id != name_id
            ).first()
            
            if existing:
                flash('Já existe um pesquisador com este nome!', 'error')
            else:
                name.name = new_name
                db.session.commit()
                flash('Pesquisador atualizado com sucesso!', 'success')
                return redirect(url_for('name'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar pesquisador: {str(e)}', 'error')
    
    return render_template('edit_name.html', name=name)

# Exclusão de Pesquisador
@app.route('/delete_researcher', methods=['POST'])
@login_required
def delete_researcher():
    researcher_id = request.form['researcher_id']
    researcher = Name.query.get(researcher_id)
    
    if not researcher:
        flash('Pesquisador não encontrado', 'error')
        return redirect(url_for('name'))
    
    # Verifica se há identificações vinculadas
    related_identifications = Identification.query.filter_by(name_id=researcher_id).count()
    if related_identifications > 0:
        flash(f'Não é possível excluir - existem {related_identifications} identificações vinculadas a este pesquisador!', 'error')
        return redirect(url_for('name'))
    
    try:
        db.session.delete(researcher)
        db.session.commit()
        flash('Pesquisador excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir pesquisador: {str(e)}', 'error')
    
    return redirect(url_for('name'))
@app.route('/edit_identification/<int:compound_id>/<int:matrix_id>/<int:name_id>', methods=['GET', 'POST'])
@login_required
def edit_identification(compound_id, matrix_id, name_id):
    # Obtém a identificação existente
    identification = Identification.query.filter_by(
        compound_id=compound_id,
        matrix_id=matrix_id,
        name_id=name_id
    ).first_or_404()
    
    # Obtém os objetos relacionados
    compound = Compound.query.get_or_404(compound_id)
    old_matrix = Matrix.query.get_or_404(matrix_id)
    researcher = Name.query.get_or_404(name_id)

    if request.method == 'POST':
        try:
            # Lógica para atualizar a matriz (organismo/tecido)
            organism = request.form['organism_select'] if request.form['organism_select'] != "_NEW_" else request.form['organism_new'].strip().title()
            plant_tissue = request.form['tissue_select'] if request.form['tissue_select'] != "_NEW_" else request.form['tissue_new'].strip().title()
            
            # Encontra ou cria a nova matriz
            new_matrix = Matrix.query.filter_by(
                organism=organism,
                plant_tissue=plant_tissue
            ).first()
            
            if not new_matrix:
                new_matrix = Matrix(organism=organism, plant_tissue=plant_tissue)
                db.session.add(new_matrix)
                db.session.flush()  # Para obter o ID
            
            # Atualiza a identificação
            identification.matrix_id = new_matrix.matrixes_id
            db.session.commit()
            
            flash('Identificação atualizada com sucesso!', 'success')
            return redirect(url_for('view_compound', compound_id=compound_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar: {str(e)}', 'error')

    # Para GET, mostra o formulário preenchido
    organisms = [m.organism for m in Matrix.query.distinct(Matrix.organism).all()]
    tissues = [m.plant_tissue for m in Matrix.query.distinct(Matrix.plant_tissue).all()]
    
    return render_template(
        'edit_identification.html',
        compound=compound,
        old_matrix=old_matrix,
        researcher=researcher,
        organisms=organisms,
        tissues=tissues
    )

@app.route('/api/analytics', methods=['POST'])
@login_required
def api_add_analytics():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()


@app.route('/export_fragments')
@login_required
def export_fragments():
    # Buscar todas as análises com seus fragmentos
    analytics = CompoundAnalytics.query.all()

    # Montar os dados em lista de dicionários
    export_data = []

    for analytic in analytics:
        for fragment in analytic.fragments:
            export_data.append({
                'compound_id': analytic.compound_id,
                'analytics_id': analytic.analytics_id,
                'fragment_id': fragment.id,
                'fragment_mz': fragment.m_z,
                'fragment_intensity': fragment.intensity
            })

    # Criar DataFrame
    df = pd.DataFrame(export_data)

    # Se quiser, pode ordenar por compound_id ou analytics_id
    df = df.sort_values(by=['compound_id', 'analytics_id'])

    # Salvar para um buffer em memória
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    # Enviar como download
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='fragments_export.csv'
    )


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('entrada'))

@app.route('/test_analytics')
def test_analytics():
    try:
        analytics = CompoundAnalytics.query.all()
        results = []
        for a in analytics:
            results.append({
                'id': a.id,
                'compound': a.compound.compound if a.compound else None,
                'matrix': a.matrix.organism if a.matrix else None,
                'has_compound': a.compound is not None,
                'has_matrix': a.matrix is not None
            })
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@login_manager.user_loader
def load_user(user_id):
    # Esta função é usada para carregar o usuário com base no ID do usuário
    return User.query.get(int(user_id))

@app.route('/debug-data')
def debug_data():
    from sqlalchemy import inspect
    analytics = CompoundAnalytics.query.limit(5).all()
    return jsonify([{c.key: getattr(a, c.key) 
                   for c in inspect(a).mapper.column_attrs} 
                   for a in analytics])

# Carrega o modelo e o scaler
modelo = joblib.load('modelo_composto.pkl')
scaler = joblib.load('scaler.pkl')

@app.route('/formulario')
def home():
    return render_template('formulario.html')  # Página com formulário

from ranking_model import rankear_por_score

@app.route('/prever', methods=['POST'])
def prever():
    try:
        fragment_mz_list = request.form.getlist('fragment_mz')
        fragment_intensity_list = request.form.getlist('fragment_intensity')
        formula_alvo = request.form.get('formula')  # opcional

        if not fragment_mz_list:
            return "Nenhum valor de m/z informado."

        fragmentos = []
        for mz, intensity in zip(fragment_mz_list, fragment_intensity_list):
            mz = float(mz)
            intensity = float(intensity) if intensity else None
            fragmentos.append((mz, intensity))

        resultados_brutos = []

        for mz, intensity in fragmentos:
            margem = 50
            query = db.session.query(Fragment, Compound).join(
                CompoundAnalytics, CompoundAnalytics.analytics_id == Fragment.compound_analytics_id
            ).join(
                Compound, Compound.compound_id == CompoundAnalytics.compound_id
            ).filter(
                Fragment.m_z.between(mz - margem, mz + margem)
            )

            if intensity is not None:
                query = query.filter(Fragment.intensity.between(intensity - margem, intensity + margem))

            matches = query.all()

            for frag, comp in matches:
                resultados_brutos.append({
                    'compound_name': comp.compound,
                    'compound_id': comp.compound_id,
                    'formula': comp.molecular_formula,
                    'm_z': frag.m_z,
                    'intensidade': frag.intensity
                })

        if not resultados_brutos:
            return "Nenhum composto encontrado."

        # Chama o modelo de ranking
        ranked = rankear_por_score(resultados_brutos, formula_alvo=formula_alvo, mz_alvo=mz, intensidade_alvo=intensity)

        return render_template('formulario.html', resultados=ranked)

    except Exception as e:
        return f"Erro ao processar a previsão: {e}"

@app.route('/analises/<int:compound_id>')
def ver_analises(compound_id):
    try:
        # Buscar o composto
        composto = Compound.query.filter_by(compound_id=compound_id).first()

        if not composto:
            return f"Composto com ID {compound_id} não encontrado."

        # Buscar análises relacionadas (CompoundAnalytics + Fragments)
        analises = CompoundAnalytics.query.filter_by(compound_id=compound_id).all()

        return render_template('analises.html', composto=composto, analises=analises)

    except Exception as e:
        return f"Erro ao buscar análises: {e}"

@app.route('/analytic/<int:analytics_id>')
def ver_analise_individual(analytics_id):
    try:
        # Buscar a análise
        analise = CompoundAnalytics.query.get(analytics_id)
        if not analise:
            return f"Análise com ID {analytics_id} não encontrada."

        # Buscar composto relacionado
        composto = Compound.query.filter_by(compound_id=analise.compound_id).first()

        return render_template('analise_individual.html', analise=analise, composto=composto)

    except Exception as e:
        return f"Erro ao buscar análise: {e}"

@app.route('/buscar_massas', methods=['GET', 'POST'])
def buscar_mass():
    resultados = None
    if request.method == 'POST':
        massa = float(request.form['massa'])
        resultados = buscar_compostos_bd(massa)
    return render_template('buscar_massas.html', resultados=resultados)

@app.route('/dashboard')
def dashboard():
    # Total de compostos cadastrados
    total_compostos = Compound.query.count()

    # Compostos mais identificados (com contagem de ocorrências)
    compostos_mais_identificados = (
        db.session.query(
            Identification.compound_id,
            Compound.compound,
            func.count().label("total")
        )
        .join(Compound, Compound.compound_id == Identification.compound_id)
        .group_by(Identification.compound_id, Compound.compound)
        .order_by(func.count().desc())
        .all()
    )
    
    # Matrizes que mais identificaram compostos
    matrizes_mais_identificadoras = (
        db.session.query(
            Identification.matrix_id,
            Matrix.organism,
            Matrix.plant_tissue,
            func.count().label("total")
        )
        .join(Matrix, Matrix.matrixes_id == Identification.matrix_id)
        .group_by(Identification.matrix_id, Matrix.organism, Matrix.plant_tissue)
        .order_by(func.count().desc())
        .all()
    )
    
    # Converter para formato serializável
    compostos_list = [{
        'compound': item.compound,
        'total': item.total
    } for item in compostos_mais_identificados]
    
    matrizes_list = [{
        'matrix_id': item.matrix_id,
        'description': f"{item.organism} - {item.plant_tissue}",
        'total': item.total
    } for item in matrizes_mais_identificadoras]
    
    return render_template('dashboard.html',
                         total_compostos=total_compostos,
                         compostos_mais_identificados=compostos_list,
                         matrizes_mais_identificadoras=matrizes_list)


# Inicialize o LoginManager com o seu aplicativo
login_manager.init_app(app)

#Flask seja iniciado somente quando o script Python for executado como um programa principal
if __name__ == '__main__':
    print("\n=== Iniciando servidor Flask ===")
    app.run(host="0.0.0.0", port=5000, debug=True)