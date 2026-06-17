data(stackloss)

# Robust analogue of the classical F-test for nested linear models:
# is the extra term `Acid.Conc.` worth keeping?
full    <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., data = stackloss)
reduced <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp, data = stackloss)

res <- rob.linear.test(full, reduced)
print(res)
