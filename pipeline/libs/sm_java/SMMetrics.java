// Harness around the Shevrin & Maoz artifact
import java.io.*;
import java.util.Locale;
import formula.Formula;
import formula.RefactorTool;
import language.ParserHelper;
import metrics.*;

public class SMMetrics {
    public static void main(String[] args) throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        System.out.println(String.join("\t", "NegationCount", "NegationLevel", "OperatorNesting",
            "OperatorCount", "ImplicationCount", "ImplicationNesting", "IffCount", "DistinctOperatorCount",
            "NegationNesting", "AndCount", "OrCount", "SM_Score"));
        String line;
        while ((line = in.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) { System.out.println(); continue; }
            Formula f = ParserHelper.parse(line);
            int[] v = {
                new NegationCount().count(f), new NegationLevel().count(f), new OperatorNesting().count(f),
                new OperatorCount().count(f), new ImplicationCount().count(f), new ImplicationNesting().count(f),
                new IffCount().count(f), new DistinctOperatorCount().count(f), new NegationNesting().count(f),
                new AndCount().count(f), new OrCount().count(f) };
            StringBuilder sb = new StringBuilder();
            for (int x : v) sb.append(x).append('\t');
            sb.append(String.format(Locale.US, "%.4f", RefactorTool.score(f)));
            System.out.println(sb);
        }
    }
}
