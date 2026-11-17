// Harness around jmltk/jmlparser, for sm_jml.py.

import java.io.*;
import java.util.*;
import com.github.javaparser.*;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.expr.*;
import com.github.javaparser.ast.jml.NodeWithContracts;
import com.github.javaparser.ast.jml.clauses.*;
import com.github.javaparser.ast.jml.expr.*;

public class SMJml {
    static String q(String s) {
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c == '\n') b.append("\\n");
            else if (c == '\t') b.append("\\t");
            else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        return b.append('"').toString();
    }
    static ConditionalExpr firstConditional(Node e) {                   // the first ?: inside e (not e itself), not under a lambda or quantifier
        for (Node child : e.getChildNodes()) {
            if (child instanceof ConditionalExpr) return (ConditionalExpr) child;
            if (child instanceof LambdaExpr || child instanceof JmlQuantifiedExpr) continue;
            ConditionalExpr found = firstConditional(child);
            if (found != null) return found;
        }
        return null;
    }
    static String json(Expression e) {                                   // json0 plus, when e contains a ?: , that conditional as "cond1"
        String base = json0(e);
        ConditionalExpr c = firstConditional(e);
        if (c == null) return base;
        return base.substring(0, base.length() - 1) + ",\"cond1\":{\"cond\":" + json(c.getCondition()) + ",\"then\":" + json(c.getThenExpr())
             + ",\"else\":" + json(c.getElseExpr()) + ",\"s\":" + q(c.toString()) + "}}";
    }
    static String json0(Expression e) {
        String text = q(e.toString());
        if (e instanceof BinaryExpr) {
            BinaryExpr b = (BinaryExpr) e;
            return "{\"t\":\"BinaryExpr\",\"op\":\"" + b.getOperator().name() + "\",\"left\":" + json(b.getLeft()) + ",\"right\":" + json(b.getRight()) + ",\"s\":" + text + "}";
        }
        if (e instanceof JmlBinaryInfixExpr) {
            JmlBinaryInfixExpr b = (JmlBinaryInfixExpr) e;
            return "{\"t\":\"JmlBinaryInfixExpr\",\"op\":" + q(b.getOperator().asString()) + ",\"left\":" + json(b.getLeft()) + ",\"right\":" + json(b.getRight()) + ",\"s\":" + text + "}";
        }
        if (e instanceof UnaryExpr) {
            UnaryExpr u = (UnaryExpr) e;
            return "{\"t\":\"UnaryExpr\",\"op\":\"" + u.getOperator().name() + "\",\"expr\":" + json(u.getExpression()) + ",\"s\":" + text + "}";
        }
        if (e instanceof EnclosedExpr) {
            return "{\"t\":\"EnclosedExpr\",\"inner\":" + json(((EnclosedExpr) e).getInner()) + ",\"s\":" + text + "}";
        }
        if (e instanceof ConditionalExpr) {
            ConditionalExpr c = (ConditionalExpr) e;
            return "{\"t\":\"ConditionalExpr\",\"cond\":" + json(c.getCondition()) + ",\"then\":" + json(c.getThenExpr()) + ",\"else\":" + json(c.getElseExpr()) + ",\"s\":" + text + "}";
        }
        if (e instanceof BooleanLiteralExpr) {
            return "{\"t\":\"BooleanLiteralExpr\",\"value\":" + ((BooleanLiteralExpr) e).getValue() + ",\"s\":" + text + "}";
        }
        if (e instanceof MethodCallExpr) {                          // s.allMatch(x -> B): expose the lambda body B
            MethodCallExpr m = (MethodCallExpr) e;
            String body = "";
            if (m.getArguments().size() == 1 && m.getArguments().get(0) instanceof LambdaExpr) {
                LambdaExpr lambda = (LambdaExpr) m.getArguments().get(0);
                if (lambda.getExpressionBody().isPresent()) body = ",\"lambda_body\":" + json(lambda.getExpressionBody().get());
            }
            if (m.getNameAsString().equals("\\old") && m.getArguments().size() == 1)             // \old(E): the expression E
                body += ",\"old_arg\":" + json(m.getArguments().get(0));
            if (m.getScope().isPresent() && m.getScope().get() instanceof MethodCallExpr) {   // s.filter(x -> R).allMatch(...): the range R
                MethodCallExpr scope = (MethodCallExpr) m.getScope().get();
                if (scope.getNameAsString().equals("filter") && scope.getArguments().size() == 1 && scope.getArguments().get(0) instanceof LambdaExpr) {
                    LambdaExpr f = (LambdaExpr) scope.getArguments().get(0);
                    if (f.getExpressionBody().isPresent()) body += ",\"filter_body\":" + json(f.getExpressionBody().get());
                }
            }
            return "{\"t\":\"MethodCallExpr\",\"name\":" + q(m.getNameAsString()) + body + ",\"s\":" + text + "}";
        }
        if (e instanceof InstanceOfExpr) return "{\"t\":\"InstanceOfExpr\",\"s\":" + text + "}";
        if (e instanceof JmlMultiCompareExpr) {                     // a <= b < c  ->  operands + operators
            JmlMultiCompareExpr mc = (JmlMultiCompareExpr) e;
            StringBuilder operands = new StringBuilder("["), ops = new StringBuilder("[");
            for (Expression x : mc.getExpressions()) operands.append(operands.length() > 1 ? "," : "").append(json(x));
            for (BinaryExpr.Operator o : mc.getOperators()) ops.append(ops.length() > 1 ? "," : "").append(q(o.asString()));
            return "{\"t\":\"JmlMultiCompareExpr\",\"operands\":" + operands + "],\"ops\":" + ops + "],\"s\":" + text + "}";
        }
        if (e instanceof JmlQuantifiedExpr) {                       // \forall T x; range; body  ->  binder + [range, body]
            JmlQuantifiedExpr qe = (JmlQuantifiedExpr) e;
            StringBuilder exprs = new StringBuilder("[");
            for (Expression x : qe.getExpressions()) exprs.append(exprs.length() > 1 ? "," : "").append(x == null ? "null" : json(x));
            return "{\"t\":\"JmlQuantifiedExpr\",\"binder\":" + q(qe.getBinder().toString()) + ",\"exprs\":" + exprs + "],\"s\":" + text + "}";
        }
        return "{\"t\":" + q(e.getClass().getSimpleName()) + ",\"s\":" + text + "}";
    }

    static void ensures(JmlContract contract, List<String> out) {
        for (JmlClause clause : contract.getClauses())
            if (clause instanceof JmlSimpleExprClause && clause.getKind() == JmlClauseKind.ENSURES)
                out.add(((JmlSimpleExprClause) clause).getExpression().toString());
        for (JmlContract sub : contract.getSubContracts()) ensures(sub, out);
    }

    static void extract(String[] files, PrintStream out) {
        JavaParser parser = new JavaParser(new ParserConfiguration().setProcessJml(true));
        for (String path : files) {
            List<String> clauses = new ArrayList<>();
            int problems = 0;
            String error = null;
            StringBuilder messages = new StringBuilder("[");
            try {
                ParseResult<CompilationUnit> result = parser.parse(new File(path));
                problems = result.getProblems().size();
                for (Problem p : result.getProblems()) messages.append(messages.length() > 1 ? "," : "").append(q(p.getVerboseMessage().replace('\n', ' ')));
                if (result.getResult().isPresent())
                    for (Node n : result.getResult().get().findAll(Node.class))
                        if (n instanceof NodeWithContracts && ((NodeWithContracts<?>) n).getContracts() != null)
                            for (JmlContract c : ((NodeWithContracts<?>) n).getContracts()) ensures(c, clauses);
            } catch (Throwable t) {
                error = t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage()).replace('\n', ' ');
            }
            StringBuilder list = new StringBuilder("[");
            for (int i = 0; i < clauses.size(); i++) list.append(i > 0 ? "," : "").append(q(clauses.get(i)));
            out.println("{\"file\":" + q(path) + ",\"problems\":" + problems + ",\"messages\":" + messages + "]"
                        + (error == null ? "" : ",\"error\":" + q(error)) + ",\"ensures\":" + list + "]}");
        }
    }

    public static void main(String[] args) throws IOException {
        PrintStream out = new PrintStream(System.out, true, "UTF-8");
        if (args.length > 0) { extract(args, out); return; }
        StaticJavaParser.getParserConfiguration().setProcessJml(true);
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, "UTF-8"));
        String line;
        while ((line = in.readLine()) != null) {
            if (line.trim().isEmpty()) { out.println("{\"error\":\"empty\"}"); continue; }
            try {
                Expression e = StaticJavaParser.parseJmlExpression(line);
                out.println(json(e));
            } catch (Throwable t) {
                out.println("{\"error\":" + q(t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage()).replace('\n', ' ')) + "}");
            }
        }
    }
}
