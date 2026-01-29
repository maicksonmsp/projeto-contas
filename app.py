"""
Sistema de Gestão de Ativos de Telecomunicações - PEIXOTO GRUPO EMPRESARIAL
VERSÃO DEFINITIVA COMPLETA COM SQLAlchemy + GLOBAL CONTEXT + PAGINAÇÃO
"""

from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
import pandas as pd
from io import BytesIO, StringIO
import csv
import os
from functools import wraps
from math import ceil

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'peixoto-grupo-empresarial-2024-secret')
db_user = os.getenv('MYSQL_USER', 'root')
db_pass = os.getenv('MYSQL_PASSWORD', 'masterof') # Senha local padrão
db_host = os.getenv('MYSQL_HOST', 'localhost')    # No K8s será 'mysql.database.svc.cluster.local'
db_name = os.getenv('MYSQL_DATABASE', 'telecom_assets')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
csrf = CSRFProtect(app)

# ========== MODELOS ==========
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('Ativo', 'Inativo'), default='Ativo')
    isAdmin = db.Column(db.Boolean, default=False)
    
    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def get_id(self):
        return str(self.id)

class Linha(db.Model):
    __tablename__ = 'linhas'
    id = db.Column(db.Integer, primary_key=True)
    conta = db.Column(db.String(30), nullable=False)
    linha = db.Column(db.String(20), nullable=False)  # Armazenado apenas números
    plano = db.Column(db.String(100), nullable=False)
    mensalidade = db.Column(db.Numeric(10, 2), nullable=False)
    responsavel = db.Column(db.String(150), nullable=False)
    departamento = db.Column(db.String(100), nullable=False)
    chipeira = db.Column(db.Enum('Sim', 'Não'), nullable=False)
    efetivacao = db.Column(db.Date, nullable=False)
    termino = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('Ativa', 'A Cancelar', 'Cancelada'), nullable=False)
    uso = db.Column(db.Enum('Sim', 'Não'), nullable=False)
    fase = db.Column(db.String(20), default=None)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conta': self.conta,
            'linha': self.formatar_telefone(self.linha),
            'linha_raw': self.linha,
            'plano': self.plano,
            'mensalidade': float(self.mensalidade),
            'responsavel': self.responsavel,
            'departamento': self.departamento,
            'chipeira': self.chipeira,
            'efetivacao': self.efetivacao.strftime('%d/%m/%Y') if self.efetivacao else None,
            'termino': self.termino.strftime('%d/%m/%Y') if self.termino else None,
            'status': self.status,
            'uso': self.uso,
            'fase': self.fase
        }
    
    def formatar_telefone(self, telefone):
        """Formata o telefone para exibição (XX) XXXXX-XXXX"""
        if not telefone:
            return ''
        
        # Remove caracteres não numéricos
        numeros = ''.join(filter(str.isdigit, str(telefone)))
        
        if len(numeros) == 11:  # Celular com DDD
            return f'({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}'
        elif len(numeros) == 10:  # Telefone fixo com DDD
            return f'({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}'
        elif len(numeros) == 9:  # Celular sem DDD
            return f'{numeros[:5]}-{numeros[5:]}'
        elif len(numeros) == 8:  # Telefone fixo sem DDD
            return f'{numeros[:4]}-{numeros[4:]}'
        else:
            return telefone

# ========== FUNÇÕES AUXILIARES ==========
def formatar_telefone_para_exibicao(telefone):
    """Função auxiliar para formatar telefone para exibição"""
    if not telefone:
        return ''
    
    # Remove caracteres não numéricos
    numeros = ''.join(filter(str.isdigit, str(telefone)))
    
    if len(numeros) == 11:  # Celular com DDD
        return f'({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}'
    elif len(numeros) == 10:  # Telefone fixo com DDD
        return f'({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}'
    elif len(numeros) == 9:  # Celular sem DDD
        return f'{numeros[:5]}-{numeros[5:]}'
    elif len(numeros) == 8:  # Telefone fixo sem DDD
        return f'{numeros[:4]}-{numeros[4:]}'
    else:
        return telefone

def limpar_telefone(telefone_formatado):
    """Remove formatação do telefone, deixando apenas números"""
    if not telefone_formatado:
        return ''
    return ''.join(filter(str.isdigit, str(telefone_formatado)))

def formatar_moeda_br(valor):
    """Formata valores monetários no formato brasileiro (R$ 48,08)"""
    try:
        if valor is None:
            return '0,00'
        
        # Converter para float
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.'))
        elif not isinstance(valor, (int, float)):
            valor = float(valor)
        
        # Formatar com 2 casas decimais e vírgula como separador decimal
        formatted = f"{valor:,.2f}"
        
        # Substituir ponto por vírgula para separador decimal
        # e vírgula por ponto para separador de milhar
        if '.' in formatted and ',' in formatted:
            # Tem separador de milhar e decimal (ex: 1,000.50)
            return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        elif '.' in formatted:
            # Apenas separador decimal (ex: 48.08)
            return formatted.replace('.', ',')
        else:
            # Número inteiro (ex: 48)
            return f"{valor},00"
    except (ValueError, TypeError) as e:
        print(f"Erro ao formatar moeda: {e}, valor: {value}")
        return '0,00'

# ========== AUTENTICAÇÃO ==========
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.isAdmin:
            flash('Acesso restrito a administradores', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ========== FILTROS DE TEMPLATE ==========
@app.template_filter('format_date')
def format_date(value, format='%d/%m/%Y'):
    """
    Filtro para formatar datas no formato brasileiro
    """
    if value is None:
        return '-'
    
    # Se for string, tenta converter para datetime
    if isinstance(value, str):
        # Tenta diferentes formatos de entrada
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S'):
            try:
                value = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
    
    # Se já for datetime/date, formata
    if isinstance(value, (datetime, date)):
        return value.strftime(format)
    
    # Se não conseguir formatar, retorna o valor original
    return str(value)

@app.template_filter('format_phone')
def format_phone(value):
    """
    Filtro para formatar números de telefone no formato brasileiro
    Entrada: 16981451024
    Saída: (16) 98145-1024
    """
    return formatar_telefone_para_exibicao(value)

@app.template_filter('format_currency')
def format_currency(value):
    """
    Formata valores monetários no formato brasileiro
    Entrada: 48.08
    Saída: 48,08
    """
    try:
        if value is None:
            return '0,00'
        
        # Converter para float
        if isinstance(value, str):
            # Remove R$, espaços e converte vírgula para ponto
            clean_value = value.replace('R$', '').replace(' ', '').strip()
            if clean_value == '':
                return '0,00'
            # Substitui vírgula por ponto para conversão
            value = float(clean_value.replace(',', '.'))
        elif not isinstance(value, (int, float)):
            value = float(value)
        
        # Formatar com 2 casas decimais
        formatted = f"{value:,.2f}"
        
        # Substituir ponto por vírgula para separador decimal
        # e vírgula por ponto para separador de milhar
        if '.' in formatted and ',' in formatted:
            # Tem separador de milhar e decimal (ex: 1,000.50)
            return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        elif '.' in formatted:
            # Apenas separador decimal (ex: 48.08)
            return formatted.replace('.', ',')
        else:
            # Número inteiro (ex: 48)
            return f"{value},00"
    except (ValueError, TypeError) as e:
        print(f"Erro ao formatar moeda: {e}, valor: {value}")
        return '0,00'

# ========== CONTEXTO GLOBAL ==========
@app.context_processor
def inject_global_data():
    return {
        'current_year': datetime.now().year,
        'now': datetime.now(),
        'app_name': 'PEIXOTO GRUPO EMPRESARIAL',
        'company_name': 'PEIXOTO GRUPO EMPRESARIAL',
        'version': '2.0'
    }

# ========== INICIALIZAR BANCO ==========
def init_db():
    """Inicializa o banco de dados"""
    try:
        print("🔧 Inicializando banco de dados...")
        
        # Criar todas as tabelas
        db.create_all()
        
        # Verificar se já existe usuário admin
        if not Usuario.query.filter_by(nome='admin').first():
            admin = Usuario(
                nome='admin',
                status='Ativo',
                isAdmin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin criado: admin / admin123")
        
        print("✅ Banco inicializado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        db.session.rollback()
        return False

# ========== ROTAS ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(nome=nome).first()
        
        if usuario:
            if usuario.check_password(senha):
                if usuario.status == 'Ativo':
                    login_user(usuario)
                    flash('Login realizado com sucesso!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Usuário inativo', 'error')
            else:
                flash('Senha incorreta', 'error')
        else:
            flash('Usuário não encontrado', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('login'))

# ========== DASHBOARD ==========
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        hoje = date.today()
        
        # Consultas otimizadas com SQLAlchemy
        total_linhas = Linha.query.count()
        
        # Cálculos agregados
        from sqlalchemy import func
        
        resultados = db.session.query(
            func.count(Linha.id).label('total'),
            func.sum(Linha.mensalidade).label('custo_total'),
            func.avg(Linha.mensalidade).label('media_mensalidade')
        ).first()
        
        # Estatísticas por status
        ativas = Linha.query.filter_by(status='Ativa').count()
        a_cancelar = Linha.query.filter_by(status='A Cancelar').count()
        canceladas = Linha.query.filter_by(status='Cancelada').count()
        
        # Distribuição por departamento
        departamentos_data = db.session.query(
            Linha.departamento,
            func.count(Linha.id).label('total'),
            func.sum(Linha.mensalidade).label('custo_total')
        ).group_by(Linha.departamento).order_by(func.count(Linha.id).desc()).all()
        
        # Status das linhas
        status_data = db.session.query(
            Linha.status,
            func.count(Linha.id).label('total')
        ).group_by(Linha.status).all()
        
        # Resumo COMPLETO
        resumo = {
            'total_linhas': total_linhas,
            'linhas_ativas': ativas,
            'linhas_a_cancelar': a_cancelar,
            'linhas_canceladas': canceladas,
            'custo_mensal_total': float(resultados.custo_total or 0),
            'media_mensalidade': float(resultados.media_mensalidade or 0),
        }
        
        return render_template('dashboard.html',
                             resumo=resumo,
                             departamentos=departamentos_data,
                             status_linhas=status_data,
                             hoje=hoje)
        
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'error')
        return redirect(url_for('login'))

# ========== GERENCIAR LINHAS COM PAGINAÇÃO ==========
@app.route('/linhas')
@login_required
def listar_linhas():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)  # Padrão: 10 linhas por página
    
    try:
        query = Linha.query
        
        # Aplicar filtro de busca
        if search:
            search_filter = f'%{search}%'
            query = query.filter(
                db.or_(
                    Linha.conta.like(search_filter),
                    Linha.linha.like(search_filter),
                    Linha.plano.like(search_filter),
                    Linha.responsavel.like(search_filter),
                    Linha.departamento.like(search_filter),
                    Linha.status.like(search_filter),
                    Linha.fase.like(search_filter)
                )
            )
        
        # Ordenar por ID decrescente (mais recentes primeiro)
        query = query.order_by(Linha.id.desc())
        
        # Paginação
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        linhas = pagination.items
        
        return render_template('linhas.html', 
                             linhas=linhas, 
                             search=search,
                             pagination=pagination,
                             per_page=per_page)
        
    except Exception as e:
        flash(f'Erro ao carregar linhas: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/linhas/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_linha():
    if request.method == 'POST':
        try:
            # Limpar e formatar o telefone antes de salvar
            telefone_raw = request.form['linha']
            telefone_limpo = limpar_telefone(telefone_raw)
            
            # Converter mensalidade para float (substituir vírgula por ponto)
            mensalidade_str = request.form['mensalidade'].replace(',', '.')
            
            nova_linha = Linha(
                conta=request.form['conta'],
                linha=telefone_limpo,  # Salvar apenas números
                plano=request.form['plano'],
                mensalidade=float(mensalidade_str),
                responsavel=request.form['responsavel'],
                departamento=request.form['departamento'],
                chipeira=request.form['chipeira'],
                efetivacao=datetime.strptime(request.form['efetivacao'], '%Y-%m-%d').date(),
                termino=datetime.strptime(request.form['termino'], '%Y-%m-%d').date(),
                status=request.form['status'],
                uso=request.form['uso'],
                fase=request.form.get('fase', '')
            )
            
            db.session.add(nova_linha)
            db.session.commit()
            flash('Linha adicionada com sucesso!', 'success')
            return redirect(url_for('listar_linhas', nova=nova_linha.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'error')
    
    return render_template('adicionar_linha.html')

@app.route('/linhas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_linha(id):
    try:
        linha = Linha.query.get_or_404(id)
        
        if request.method == 'POST':
            # Limpar e formatar o telefone antes de salvar
            telefone_raw = request.form['linha']
            telefone_limpo = limpar_telefone(telefone_raw)
            
            # Converter mensalidade para float (substituir vírgula por ponto)
            mensalidade_str = request.form['mensalidade'].replace(',', '.')
            
            linha.conta = request.form['conta']
            linha.linha = telefone_limpo  # Salvar apenas números
            linha.plano = request.form['plano']
            linha.mensalidade = float(mensalidade_str)
            linha.responsavel = request.form['responsavel']
            linha.departamento = request.form['departamento']
            linha.chipeira = request.form['chipeira']
            linha.efetivacao = datetime.strptime(request.form['efetivacao'], '%Y-%m-%d').date()
            linha.termino = datetime.strptime(request.form['termino'], '%Y-%m-%d').date()
            linha.status = request.form['status']
            linha.uso = request.form['uso']
            linha.fase = request.form.get('fase', '')
            
            db.session.commit()
            flash('Linha atualizada com sucesso!', 'success')
            return redirect(url_for('listar_linhas'))
        
        return render_template('editar_linha.html', linha=linha)
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('listar_linhas'))

@app.route('/linhas/excluir/<int:id>', methods=['POST'])
@login_required
@admin_required
def excluir_linha(id):
    try:
        linha = Linha.query.get_or_404(id)
        db.session.delete(linha)
        db.session.commit()
        flash('Linha excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir linha: {str(e)}', 'error')
    
    return redirect(url_for('listar_linhas'))

# ========== EXPORTAÇÃO (CSV E EXCEL) ==========
@app.route('/exportar/linhas')
@login_required
def exportar_linhas():
    """Redireciona para exportação CSV (mantém compatibilidade)"""
    return redirect(url_for('exportar_linhas_csv'))

@app.route('/exportar/linhas/csv')
@login_required
def exportar_linhas_csv():
    try:
        linhas = Linha.query.order_by(Linha.id).all()
        
        # Criar CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow(['ID', 'Conta', 'Linha', 'Plano', 'Mensalidade (R$)', 
                        'Responsável', 'Departamento', 'Chipeira', 'Efetivação', 
                        'Término', 'Status', 'Em Uso', 'Fase'])
        
        # Dados
        for linha in linhas:
            writer.writerow([
                linha.id,
                linha.conta,
                formatar_telefone_para_exibicao(linha.linha),  # Formatar para exibição
                linha.plano,
                formatar_moeda_br(linha.mensalidade),  # Formatar moeda
                linha.responsavel,
                linha.departamento,
                linha.chipeira,
                linha.efetivacao.strftime('%d/%m/%Y') if linha.efetivacao else '',
                linha.termino.strftime('%d/%m/%Y') if linha.termino else '',
                linha.status,
                linha.uso,
                linha.fase or ''
            ])
        
        output.seek(0)
        
        # Retornar arquivo
        hoje = date.today().strftime('%Y-%m-%d')
        filename = f'linhas_telefonicas_{hoje}.csv'
        
        return send_file(
            BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Erro ao exportar CSV: {str(e)}', 'error')
        return redirect(url_for('listar_linhas'))

@app.route('/exportar/linhas/excel')
@login_required
def exportar_linhas_excel():
    try:
        linhas = Linha.query.order_by(Linha.id).all()
        
        # Converter para lista de dicionários
        dados = []
        for linha in linhas:
            dados.append({
                'ID': linha.id,
                'Conta': linha.conta,
                'Linha Telefônica': formatar_telefone_para_exibicao(linha.linha),
                'Plano': linha.plano,
                'Mensalidade': f"R$ {formatar_moeda_br(linha.mensalidade)}",
                'Responsável': linha.responsavel,
                'Departamento': linha.departamento,
                'Chipeira': linha.chipeira,
                'Data de Efetivação': linha.efetivacao.strftime('%d/%m/%Y') if linha.efetivacao else '',
                'Data de Término': linha.termino.strftime('%d/%m/%Y') if linha.termino else '',
                'Status': linha.status,
                'Em Uso': linha.uso,
                'Fase': linha.fase or ''
            })
        
        # Criar DataFrame
        df = pd.DataFrame(dados)
        
        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Linhas Telefônicas', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Linhas Telefônicas']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Retornar arquivo
        hoje = date.today().strftime('%Y-%m-%d')
        filename = f'linhas_telefonicas_{hoje}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Erro ao exportar Excel: {str(e)}', 'error')
        return redirect(url_for('listar_linhas'))

# ========== GERENCIAR USUÁRIOS ==========
@app.route('/usuarios')
@login_required
@admin_required
def listar_usuarios():
    try:
        usuarios = Usuario.query.order_by(Usuario.id).all()
        return render_template('usuarios.html', usuarios=usuarios)
    except Exception as e:
        flash(f'Erro ao carregar usuários: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/usuarios/adicionar', methods=['POST'])
@login_required
@admin_required
def adicionar_usuario():
    try:
        data = request.get_json()
        
        # Verificar se usuário já existe
        if Usuario.query.filter_by(nome=data['nome']).first():
            return jsonify({'success': False, 'error': 'Usuário já existe'})
        
        novo_usuario = Usuario(
            nome=data['nome'],
            status=data.get('status', 'Ativo'),
            isAdmin=data.get('isAdmin', False)
        )
        novo_usuario.set_password(data['senha'])
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({'success': True, 'id': novo_usuario.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/usuarios/atualizar/<int:id>', methods=['POST'])
@login_required
@admin_required
def atualizar_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        data = request.get_json()
        
        if 'nome' in data:
            usuario.nome = data['nome']
        
        if 'status' in data:
            usuario.status = data['status']
        
        if 'isAdmin' in data:
            usuario.isAdmin = data['isAdmin']
        
        if 'senha' in data and data['senha']:
            usuario.set_password(data['senha'])
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/usuarios/excluir/<int:id>', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(id):
    if id == current_user.id:
        return jsonify({'success': False, 'error': 'Não pode excluir seu próprio usuário'})
    
    try:
        usuario = Usuario.query.get_or_404(id)
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ========== API PARA DASHBOARD ==========
@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    try:
        total_linhas = Linha.query.count()
        ativas = Linha.query.filter_by(status='Ativa').count()
        a_cancelar = Linha.query.filter_by(status='A Cancelar').count()
        canceladas = Linha.query.filter_by(status='Cancelada').count()
        
        from sqlalchemy import func
        resultado = db.session.query(
            func.sum(Linha.mensalidade).label('custo_total'),
            func.avg(Linha.mensalidade).label('media_mensalidade')
        ).first()
        
        return jsonify({
            'success': True,
            'data': {
                'total_linhas': total_linhas,
                'linhas_ativas': ativas,
                'linhas_a_cancelar': a_cancelar,
                'linhas_canceladas': canceladas,
                'custo_mensal_total': float(resultado.custo_total or 0),
                'media_mensalidade': float(resultado.media_mensalidade or 0)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== API PARA PAGINAÇÃO ==========
@app.route('/api/linhas')
@login_required
def api_listar_linhas():
    """API para paginação AJAX (opcional)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        query = Linha.query
        
        if search:
            search_filter = f'%{search}%'
            query = query.filter(
                db.or_(
                    Linha.conta.like(search_filter),
                    Linha.linha.like(search_filter),
                    Linha.plano.like(search_filter),
                    Linha.responsavel.like(search_filter),
                    Linha.departamento.like(search_filter),
                    Linha.status.like(search_filter)
                )
            )
        
        query = query.order_by(Linha.id.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        linhas_data = [linha.to_dict() for linha in pagination.items]
        
        return jsonify({
            'success': True,
            'data': linhas_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== ROTA PARA TESTE ==========
@app.route('/teste')
def teste():
    """Rota para testar se o sistema está funcionando"""
    return jsonify({
        'status': 'online',
        'app': 'PEIXOTO GRUPO EMPRESARIAL',
        'database': 'OK' if Linha.query.first() else 'No data',
        'usuarios': Usuario.query.count()
    })

# ========== INICIALIZAÇÃO ==========
if __name__ == '__main__':
    with app.app_context():
        if init_db():
            print("=" * 60)
            print("✅ SISTEMA PEIXOTO GRUPO EMPRESARIAL - SQLAlchemy Edition")
            print("=" * 60)
            print("🌐 URL: http://localhost:5000")
            print("👤 Usuário: admin")
            print("🔑 Senha: admin123")
            print("=" * 60)
            print("📱 TELEFONE: Banco armazena apenas números (16981451024)")
            print("📱 EXIBIÇÃO: Interface mostra formatado ((16) 98145-1024)")
            print("💰 MOEDA: Formato brasileiro (R$ 48,08)")
            print("📊 STATUS DISPONÍVEIS: Ativa, A Cancelar, Cancelada")
            print("📈 EXPORTAÇÕES: CSV e Excel disponíveis")
            print("📄 PAGINAÇÃO: 10 linhas por página (configurável)")
            print("🔗 Rota de compatibilidade: /exportar/linhas")
            print("=" * 60)
            app.run(debug=True, host='0.0.0.0', port=5000)
        else:
            print("❌ Não foi possível iniciar o sistema. Verifique os erros acima.")