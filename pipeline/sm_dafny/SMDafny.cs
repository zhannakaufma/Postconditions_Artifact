// Parse Dafny `ensures` clauses with Dafny's own parser (DafnyCore) and print one
// JSON syntax tree per input line, for sm_dafny.py.  Each line is wrapped as
// `method M() ensures <line>` and parsed (not resolved), so parentheses survive as
// ParensExpression nodes.  Errors print as {"error": "..."}.
//
// With file arguments it instead extracts: for each .dfy file it prints
// {"file": ..., "errors": n, "ensures": [every ensures clause of every method,
// function, lemma or predicate, as written]}.
using System.Text.Json;
using Microsoft.Dafny;

class SMDafny {
  static string source = "";

  static string Text(Expression e) {                          // the source text, minus any comments inside it
    var bytes = System.Text.Encoding.UTF8.GetBytes(source);   // token positions are byte offsets
    var sb = new System.Text.StringBuilder();
    for (var t = e.StartToken; t != null; t = t.Next) {
      sb.Append(t.val);
      if (t == e.EndToken || t.Next == null) break;
      var gapStart = t.pos + System.Text.Encoding.UTF8.GetByteCount(t.val);
      var gap = t.Next.pos >= gapStart ? System.Text.Encoding.UTF8.GetString(bytes, gapStart, t.Next.pos - gapStart) : " ";
      sb.Append(string.IsNullOrWhiteSpace(gap) ? gap : " ");
    }
    return sb.ToString();
  }

  static ITEExpr? FirstConditional(Expression e) {                   // the first if-then-else inside e (not e itself), not under a lambda or comprehension
    foreach (var child in e.SubExpressions) {
      if (child is ITEExpr ite) return ite;
      if (child is LambdaExpr || child is ComprehensionExpr) continue;
      var found = FirstConditional(child);
      if (found != null) return found;
    }
    return null;
  }

  static Dictionary<string, object?> Node(Expression e) {
    var n = new Dictionary<string, object?> { ["t"] = e.GetType().Name, ["s"] = Text(e) };
    var c = FirstConditional(e);
    if (c != null) n["cond1"] = new Dictionary<string, object?> { ["cond"] = Node(c.Test), ["then"] = Node(c.Thn), ["else"] = Node(c.Els), ["s"] = Text(c) };
    switch (e) {
      case ParensExpression p: n["inner"] = Node(p.E); break;
      case BinaryExpr b: n["op"] = b.Op.ToString(); n["left"] = Node(b.E0); n["right"] = Node(b.E1); break;
      case UnaryOpExpr u: n["op"] = u.Op.ToString(); n["expr"] = Node(u.E); break;
      case ITEExpr i: n["cond"] = Node(i.Test); n["then"] = Node(i.Thn); n["else"] = Node(i.Els); break;
      case QuantifierExpr qe: n["range"] = qe.Range == null ? null : Node(qe.Range); n["term"] = Node(qe.Term); break;   // forall x | R :: T
      case OldExpr o: n["expr"] = Node(o.Expr); break;                                                                      // old(E)
      case LetExpr l: n["body"] = Node(l.Body); break;                                                                   // var x := e; body
      case ChainingExpression ce:                                                                                        // 0 <= i < n
        n["operands"] = ce.Operands.Select(Node).ToList(); n["ops"] = ce.Operators.Select(o => o.ToString()).ToList(); break;
      case LiteralExpr l: n["value"] = l.Value is bool v ? v : null; break;
    }
    return n;
  }

  static void Ensures(ModuleDefinition module, List<string> clauses) {
    foreach (var decl in module.TopLevelDecls) {
      if (decl is LiteralModuleDecl m) Ensures(m.ModuleDef, clauses);
      if (decl is TopLevelDeclWithMembers c)
        foreach (var member in c.Members)
          if (member is MethodOrFunction f)
            foreach (var ens in f.Ens) clauses.Add(Text(ens.E));
    }
  }

  static async Task Main(string[] args) {
    var options = new DafnyOptions(TextReader.Null, TextWriter.Null, TextWriter.Null);
    if (args.Length > 0) {                                     // extract mode
      foreach (var path in args) {
        try {
          source = File.ReadAllText(path);
          var reporter = new BatchErrorReporter(options);
          var result = await ProgramParser.Parse(source, new Uri(Path.GetFullPath(path)), reporter);
          var clauses = new List<string>();
          var errors = reporter.Count(ErrorLevel.Error);
          if (errors == 0) Ensures(result.Program.DefaultModuleDef, clauses);
          Console.WriteLine(JsonSerializer.Serialize(new { file = path, errors, ensures = clauses }));
        } catch (Exception ex) {
          Console.WriteLine(JsonSerializer.Serialize(new { file = path, errors = 1, error = ex.GetType().Name + ": " + ex.Message, ensures = new List<string>() }));
        }
      }
      return;
    }
    var uri = new Uri("file:///in.dfy");
    string? line;
    while ((line = Console.ReadLine()) != null) {
      source = "method M() ensures " + line + "\n";
      try {
        var reporter = new BatchErrorReporter(options);
        var result = await ProgramParser.Parse(source, uri, reporter);
        if (reporter.Count(ErrorLevel.Error) > 0) {
          var msg = reporter.AllMessagesByLevel[ErrorLevel.Error][0].Message;
          Console.WriteLine(JsonSerializer.Serialize(new { error = msg }));
          continue;
        }
        var method = result.Program.DefaultModuleDef.DefaultClass!.Members.OfType<Method>().First();
        Console.WriteLine(JsonSerializer.Serialize(Node(method.Ens[0].E)));
      } catch (Exception ex) {
        Console.WriteLine(JsonSerializer.Serialize(new { error = ex.GetType().Name + ": " + ex.Message }));
      }
    }
  }
}
